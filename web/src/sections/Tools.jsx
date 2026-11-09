import React, { useState } from 'react'
import { parse, today, addDays, daysBetween, fmt, monthsDiff, COUNTRIES, monthLabel } from '../lib.js'

const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export function Tools({ vb }) {
  const t = today()
  const [gpEnd, setGpEnd] = useState(iso(addDays(t, 14)))
  const [gpI94, setGpI94] = useState('')
  const [optType, setOptType] = useState('90')
  const [optUsed, setOptUsed] = useState('0')
  const [pdCat, setPdCat] = useState('EB-2')
  const [pdCountry, setPdCountry] = useState('in')
  const [pdDate, setPdDate] = useState('')
  const [ds, setDs] = useState('')

  const end = parse(gpEnd), i94 = parse(gpI94)
  let gp = 'Enter your last day of employment.'
  if (end) {
    const g = addDays(end, 60), last = i94 && i94 < g ? i94 : g, left = daysBetween(t, last)
    gp = <>Grace period ends <b>{fmt(last)}</b>{i94 && i94 < g ? ' (capped by your I-94)' : ''}. {left >= 0 ? <>That's <b>{left}</b> days from today.</> : 'That date has passed.'} By then you need a new petition filed, a change of status, or to leave the US.</>
  }

  const lim = +optType, used = Math.max(0, +optUsed || 0), left = lim - used
  const opt = left > 0 ? <><b>{left}</b> unemployment days left of {lim}.</> : <>You've used all {lim} days. Contact your DSO right away.</>

  const cats = vb ? [...Object.keys(vb.charts.eb.fad), ...Object.keys(vb.charts.fb.fad)] : []
  let pd = 'Enter your priority date.'
  const pdd = parse(pdDate)
  if (vb && pdd) {
    const kind = vb.charts.eb.fad[pdCat] ? 'eb' : 'fb'
    const fad = vb.charts[kind].fad[pdCat]?.[pdCountry], dff = vb.charts[kind].dff[pdCat]?.[pdCountry]
    const isCur = v => v === 'C' || (v && v !== 'U' && pdd < parse(v))
    if (fad === 'U') pd = <>{pdCat} is <b>unavailable</b> for this country in the {monthLabel(vb.month)} bulletin.</>
    else if (isCur(fad)) pd = <>Your date is <b>current</b> for final action in the {monthLabel(vb.month)} bulletin.</>
    else pd = <>You're <b>{Math.round(monthsDiff(parse(fad), pdd))} months</b> behind the final action date ({fmt(parse(fad))}).{isCur(dff) ? ' You are current on the dates for filing chart, so you may be able to file if USCIS accepts that chart this month.' : ''}</>
  }

  const dsd = parse(ds)
  return (
    <section className="card" aria-labelledby="toolH">
      <h2 id="toolH">Tools</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <details className="tool" open><summary>Is my priority date current?</summary><div className="tb">
          <div className="frow">
            <div className="field"><label htmlFor="pdc">Category</label><select id="pdc" value={pdCat} onChange={e => setPdCat(e.target.value)}>{cats.map(c => <option key={c}>{c}</option>)}</select></div>
            <div className="field"><label htmlFor="pdn">Country of chargeability</label><select id="pdn" value={pdCountry} onChange={e => setPdCountry(e.target.value)}>{COUNTRIES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
          </div>
          <div className="field"><label htmlFor="pdd">Priority date</label><input id="pdd" type="date" value={pdDate} onChange={e => setPdDate(e.target.value)} /></div>
          <div className="result">{vb ? pd : 'The Visa Bulletin is not available right now.'}</div>
        </div></details>
        <details className="tool"><summary>H-1B grace period</summary><div className="tb">
          <div className="frow">
            <div className="field"><label htmlFor="gpe">Last day of employment</label><input id="gpe" type="date" value={gpEnd} onChange={e => setGpEnd(e.target.value)} /></div>
            <div className="field"><label htmlFor="gpi">I-94 expiry</label><input id="gpi" type="date" value={gpI94} onChange={e => setGpI94(e.target.value)} /></div>
          </div>
          <div className="result">{gp}</div>
          <div className="small muted">Up to 60 consecutive days or until your I-94 ends, whichever comes first. Available once per authorized validity period.</div>
        </div></details>
        <details className="tool"><summary>OPT unemployment days</summary><div className="tb">
          <div className="frow">
            <div className="field"><label htmlFor="opt">OPT type</label><select id="opt" value={optType} onChange={e => setOptType(e.target.value)}><option value="90">Post-completion OPT (90 days)</option><option value="150">With STEM extension (150 total)</option></select></div>
            <div className="field"><label htmlFor="optu">Unemployed days used</label><input id="optu" type="number" min="0" max="150" value={optUsed} onChange={e => setOptUsed(e.target.value)} /></div>
          </div>
          <div className="result">{opt}</div>
        </div></details>
        <details className="tool"><summary>Days since filing</summary><div className="tb">
          <div className="field"><label htmlFor="ds">Receipt date</label><input id="ds" type="date" value={ds} onChange={e => setDs(e.target.value)} /></div>
          <div className="result">{dsd ? <><b>{daysBetween(dsd, t)}</b> days ({monthsDiff(dsd, t).toFixed(1)} months) since {fmt(dsd)}.</> : 'Pick the date on your receipt notice.'}</div>
        </div></details>
      </div>
      <div className="small muted">Nothing you enter here is saved or sent anywhere.</div>
    </section>
  )
}
