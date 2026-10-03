// 九个默认学科各一支"彩笔"色，饱和度压低，放在纸张底色上不刺眼。
const PALETTE = [
  '#c2453b', // 语文 朱红
  '#2f5fa7', // 数学 靛蓝
  '#8a5cb5', // 英语 紫藤
  '#d98324', // 物理 琥珀
  '#2a8f8a', // 化学 青碧
  '#4f9a45', // 生物 草绿
  '#b8487a', // 政治 洋红
  '#8c6a3f', // 历史 赭石
  '#3f7fb5', // 地理 天青
]

export function subjectColor(subjectId: number): string {
  // 用户新增的学科 ID 超出调色板时循环取色
  return PALETTE[(subjectId - 1 + PALETTE.length) % PALETTE.length]
}
