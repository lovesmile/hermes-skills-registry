#!/usr/bin/env python3
"""
hermes-memory-audit — 四层存储审计脚本

用法:
  python3 audit.py                    # 审计默认路径 ~/.hermes/memories/
  python3 audit.py /path/to/memories  # 审计指定路径

功能:
  - 统计 MEMORY.md / USER.md 各条目字数、总量 vs 限制
  - 检测常见问题：指令式表述、进度日志、疑似陈旧条目、可迁移到 skills 的内容
  - 给出优化建议
"""

import os
import re
import sys
from pathlib import Path

MEMORY_LIMIT = 2200
USER_LIMIT = 1375

DELIMITER = "§"


def load_entries(filepath: str, label: str, limit: int):
    """Read a memory file and split into entries."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ {label} ({filepath}): 文件不存在")
        return []

    raw = path.read_text(encoding="utf-8")
    entries = [e.strip() for e in raw.split(DELIMITER) if e.strip()]

    total_chars = len(raw)

    print(f"\n{'='*60}")
    print(f"📁 {label}  ({filepath})")
    print(f"{'='*60}")
    print(f"  总字符: {total_chars} / {limit}  ({'✅' if total_chars <= limit else '❌ 超出!'})")
    print(f"  条目数: {len(entries)}")
    print()

    for i, entry in enumerate(entries, 1):
        char_count = len(entry)
        bar = "█" * min(char_count // 20, 50)
        print(f"  [{i}] {char_count:>4}字 {bar}")
        # Print first 80 chars inline
        preview = entry[:80].replace("\n", " ")
        print(f"      → {preview}{'…' if len(entry) > 80 else ''}")
        print()

    return entries, total_chars


def detect_issues(entries, label: str):
    """Detect common memory anti-patterns."""
    print(f"\n  🔍 问题检测 ({label}):")
    found_any = False

    for i, entry in enumerate(entries, 1):
        issues = []

        # 1. Instruction-style ("记得/要/必须") — should be declarative
        if re.search(r"^(记得|要|必须|一定要|每次|先)", entry):
            issues.append("指令式开头（记得/要/必须）→ 应为声明式")

        # 2. Progress logs (PR numbers, bug IDs, commit SHAs)
        if re.search(r"(PR\s*#|#\d{4,}|commit\s+[a-f0-9]{7,}|Phase\s+\d|修复了?\s*bug)", entry, re.I):
            issues.append("进度日志（PR/commit/bug编号）→ 应靠 session_search")

        # 3. Temporary task state
        if re.search(r"(进行中|已完成|待处理|下一步)", entry):
            issues.append("临时任务状态 → 会话上下文即可")

        # 4. Stale content (dated more than 30 days ago — heuristic)
        date_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", entry)
        if date_match:
            issues.append(f"包含日期 {date_match.group(0)} → 检查是否已过时")

        # 5. Potential skill candidate (long procedural content)
        if len(entry) > 300:
            issues.append("内容较长（>300字），可能是流程性知识 → 考虑迁移到 skills")

        # 6. Imperative phrasing
        if re.search(r"(不要|别|禁止)", entry):
            issues.append("含否定指令 → 应为声明式（如 '项目用 pytest' 而非 '别用 unittest'）")

        if issues:
            found_any = True
            print(f"    条目 [{i}]:")
            for issue in issues:
                print(f"      ⚠️  {issue}")

    if not found_any:
        print(f"      ✅ 未发现明显问题")


def suggest_optimizations(entries, total_chars, limit, label: str):
    """Suggest space optimization strategies."""
    if total_chars <= limit * 0.8:
        return  # Under 80% — no need

    print(f"\n  💡 优化建议 ({label}):")
    overage = total_chars - limit

    if overage > 0:
        print(f"      超出 {overage} 字，建议：")
    else:
        print(f"      剩余 {limit - total_chars} 字，但接近上限，建议：")

    print("      • 同类条目合并：同一主题的分散条目→用斜线/逗号整合")
    print("      • 去掉主语/修饰词：'用户偏好是'→''、'希望/需要/要'→''")
    print("      • 长流程内容→迁移到 skills，memory 只留摘要+技能名")
    print("      • 检查是否有7天内会过时的事实（PR编号、具体日期）")

    # Find merge candidates
    print()
    print("      可考虑合并的条目组（按长度排序）：")
    sorted_entries = sorted(enumerate(entries, 1), key=lambda x: len(x[1]), reverse=True)
    for idx, (num, entry) in enumerate(sorted_entries[:3], 1):
        preview = entry[:60].replace("\n", " ")
        print(f"      [{idx}] 条目{num} ({len(entry)}字): {preview}…")


def main():
    if len(sys.argv) > 1:
        mem_dir = Path(sys.argv[1])
    else:
        hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        mem_dir = hermes_home / "memories"

    if not mem_dir.exists():
        print(f"❌ 目录不存在: {mem_dir}")
        sys.exit(1)

    print(f"🔎 Hermes 四层存储审计")
    print(f"   目录: {mem_dir}")
    print()

    # MEMORY.md
    mem_path = mem_dir / "MEMORY.md"
    result = load_entries(str(mem_path), "MEMORY.md (memory)", MEMORY_LIMIT)
    if result:
        entries, total = result
        detect_issues(entries, "memory")
        suggest_optimizations(entries, total, MEMORY_LIMIT, "memory")

    # USER.md
    user_path = mem_dir / "USER.md"
    result = load_entries(str(user_path), "USER.md (user profile)", USER_LIMIT)
    if result:
        entries, total = result
        detect_issues(entries, "user profile")
        suggest_optimizations(entries, total, USER_LIMIT, "user profile")

    # Skills audit
    skills_dir = mem_dir.parent / "skills"
    if skills_dir.exists():
        print(f"\n{'='*60}")
        print(f"📂 Skills 目录概览")
        print(f"{'='*60}")
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        print(f"  技能数: {len(skill_dirs)}")
        for sd in sorted(skill_dirs):
            skill_md = sd / "SKILL.md"
            if skill_md.exists():
                size = len(skill_md.read_text(encoding="utf-8"))
                print(f"  📄 {sd.name}: {size}字")


if __name__ == "__main__":
    main()
