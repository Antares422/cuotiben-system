/** 把服务端的 UTC 时间显示成 "2026-10-03 16:30"；不传时区就用浏览器所在时区。 */
export function formatDateTime(iso: string, timeZone?: string): string {
  // sv-SE 的日期格式恰好是 "年-月-日 时:分"
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(iso))
}
