#!/usr/bin/env bash
# 统计各迭代 tasks.md 的完成进度：数复选框，进度数字永远和文件一致，不用手工维护。
# 用法：tools/progress.sh
cd "$(dirname "$0")/.." || exit 1
shopt -s nullglob
files=(specs/*/tasks.md)
[ ${#files[@]} -eq 0 ] && { echo "还没有任何 tasks.md"; exit 0; }
for f in "${files[@]}"; do
  done_n=$(grep -c -E '^- \[[xX]\] T[0-9]+' "$f")
  todo_n=$(grep -c -E '^- \[ \] T[0-9]+' "$f")
  total=$((done_n + todo_n))
  pct=0; [ "$total" -gt 0 ] && pct=$((done_n * 100 / total))
  printf '%s\n  已完成 %d / %d（%d%%）\n' "$(dirname "$f")" "$done_n" "$total" "$pct"
  # 按阶段列出
  awk -v d="$done_n" '
    /^## Phase/ { if (name) printf "    %-46s %d/%d\n", name, ok, n; name=$0; sub(/^## /,"",name); ok=0; n=0 }
    /^- \[[xX]\] T[0-9]+/ { n++; ok++ }
    /^- \[ \] T[0-9]+/ { n++ }
    END { if (name) printf "    %-46s %d/%d\n", name, ok, n }' "$f"
done
