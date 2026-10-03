#!/usr/bin/env bash
# 统计 tasks.md 的完成进度（数复选框，进度永远和文件一致，不用手工维护），并按负责人汇总。
# 认领方式：在任务编号后写 @姓名，例如  - [ ] T001 @林亮炜 [US1] 描述
# 用法：tools/progress.sh              统计 specs/*/tasks.md
#       tools/progress.sh 某个文件.md   统计指定文件
cd "$(dirname "$0")/.." || exit 1
shopt -s nullglob
if [ $# -gt 0 ]; then files=("$@"); else files=(specs/*/tasks.md); fi
[ ${#files[@]} -eq 0 ] && { echo "还没有任何 tasks.md"; exit 0; }
for f in "${files[@]}"; do
  awk -v name="$(dirname "$f")" '
    function pct(a, b) { return b ? int(a * 100 / b) : 0 }
    /^## Phase/ { if (ph) phases[++np] = sprintf("    %-50s %d/%d", ph, pd, pt); ph=$0; sub(/^## /,"",ph); pd=0; pt=0 }
    /^- \[[ xX]\] T[0-9]+/ {
      total++; pt++
      isdone = ($0 ~ /^- \[[xX]\]/)
      if (isdone) { done++; pd++ }
      if (match($0, /@[^ ]+/)) {
        who = substr($0, RSTART, RLENGTH); own_t[who]++; if (isdone) own_d[who]++
        if (!(who in seen)) { seen[who] = 1; order[++no] = who }
      } else { free++ }
    }
    END {
      if (ph) phases[++np] = sprintf("    %-50s %d/%d", ph, pd, pt)
      printf "%s\n  已完成 %d / %d（%d%%）\n", name, done, total, pct(done, total)
      for (i = 1; i <= np; i++) print phases[i]
      printf "  负责人\n"
      for (i = 1; i <= no; i++) { w = order[i]; printf "    %-12s %d/%d\n", w, own_d[w], own_t[w] }
      printf "    %-12s %d 个任务\n", "未认领", free
    }' "$f"
done
