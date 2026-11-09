export const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export const COUNTRIES = [['all', 'All chargeability'], ['cn', 'China (mainland)'], ['in', 'India'], ['mx', 'Mexico'], ['ph', 'Philippines']]
export const TOPICS = [['all', 'All'], ['h1b', 'H-1B'], ['gc', 'Green card'], ['students', 'Students'], ['work_visas', 'Other work visas'],
  ['family', 'Family'], ['citizenship', 'Citizenship'], ['humanitarian', 'Humanitarian'], ['fees', 'Fees'], ['travel', 'Travel']]
export const KIND_LABEL = { final_rule: 'Final rule', proposed_rule: 'Proposed rule', notice: 'Notice', presidential: 'Presidential action',
  agency_news: 'Agency news', court: 'Court', legislation: 'Legislation', law_firm: 'Law firm', media: 'Media', calendar: 'Calendar' }
export const CONFIDENCE = { high: ['Official date', 'p-ok'], medium: ['Found in text', 'p-info'], ai: ['AI-extracted, verify', 'p-warn'], typical: ['Typical, not announced', 'p-plain'] }

export const parse = s => { if (!s) return null; const [y, m, d] = s.slice(0, 10).split('-').map(Number); return new Date(y, m - 1, d) }
export const today = () => { const t = new Date(); t.setHours(0, 0, 0, 0); return t }
export const DAY = 864e5
export const daysBetween = (a, b) => Math.round((b - a) / DAY)
export const addDays = (d, n) => new Date(d.getTime() + n * DAY)
export const fmt = d => d ? `${String(d.getDate()).padStart(2, '0')} ${MON[d.getMonth()]} ${d.getFullYear()}` : '—'
export const fmtShort = d => d ? `${d.getDate()} ${MON[d.getMonth()]}` : '—'
export const fmtVB = v => {
  if (v === 'C' || v === 'U') return v
  const d = parse(v)
  return d ? `${String(d.getDate()).padStart(2, '0')}${MON[d.getMonth()].toUpperCase()}${String(d.getFullYear()).slice(2)}` : '—'
}
export const monthsDiff = (a, b) => (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth()) + (b.getDate() - a.getDate()) / 30.4
export const ago = iso => {
  if (!iso) return 'never'
  const h = (Date.now() - new Date(iso).getTime()) / 36e5
  if (h < 1) return 'just now'
  if (h < 48) return `${Math.round(h)}h ago`
  return `${Math.round(h / 24)} days ago`
}
export const monthLabel = ym => { if (!ym) return ''; const [y, m] = ym.split('-').map(Number); return `${MON[m - 1]} ${y}` }

const BASE = import.meta.env.BASE_URL
export async function loadJSON(path) {
  try {
    const r = await fetch(`${BASE}data/${path}`, { cache: 'no-cache' })
    if (!r.ok) return null
    return await r.json()
  } catch {
    return null
  }
}
