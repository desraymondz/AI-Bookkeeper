// See planning/02-design.md#9-number-and-date-formatting

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function formatMoney(value: string, { parens = true }: { parens?: boolean } = {}): string {
  const trimmed = value.trim()
  const negative = trimmed.startsWith('-')
  const [whole = '0', fraction = ''] = trimmed.replace(/^[-+]/, '').split('.')
  const cents = `${fraction}00`.slice(0, 2)
  const digits = whole.replace(/^0+(?=\d)/, '')
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const text = `${grouped}.${cents}`
  if (!negative || /^0+\.00$/.test(`${digits}.${cents}`)) return text
  return parens ? `(${text})` : `-${text}`
}

export function isZero(value: string): boolean {
  return /^-?0*(\.0*)?$/.test(value.trim())
}

function parts(iso: string): [number, number, number] {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return [y ?? 0, m ?? 1, d ?? 1]
}

export function formatDate(iso: string): string {
  const [y, m, d] = parts(iso)
  return `${d} ${MONTHS[m - 1]} ${y}`
}

export function formatRange(start: string, end: string): string {
  const [sy, sm, sd] = parts(start)
  const [ey, em] = parts(end)
  if (sy === ey && sm === em) return `${sd} to ${formatDate(end)}`
  return `${formatDate(start)} to ${formatDate(end)}`
}

export function formatTimestamp(iso: string, timeZone = 'Asia/Singapore'): string {
  const date = new Date(iso)
  const fmt = new Intl.DateTimeFormat('en-SG', {
    timeZone,
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  })
  const p = Object.fromEntries(fmt.formatToParts(date).map((x) => [x.type, x.value]))
  return `${p.day} ${p.month} ${p.year}, ${p.hour}:${p.minute}`
}
