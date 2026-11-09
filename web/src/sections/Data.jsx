import React, { useMemo, useState } from 'react'
import { COUNTRIES, fmtVB, monthLabel, ago, fmt, parse } from '../lib.js'

const TONE = { good: ['p-ok', 'Better'], bad: ['p-bad', 'Worse'], neutral: ['p-plain', 'Update'] }

function Seg({ value, options, onChange, label }) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map(([v, l]) => <button key={v} aria-pressed={value === v} onClick={() => onChange(v)}>{l}</button>)}
    </div>
  )
}

function Unavailable({ what }) {
  return <div className="empty">{what} isn't available right now. The last update failed; see Data sources at the bottom of the page.</div>
}

export function Changes({ data }) {
  const items = data?.items || []
  if (!items.length) return <div className="empty">No changes yet. Changes appear once there are two updates to compare.</div>
  return (
    <div className="changes">
      {items.map((c, i) => (
        <div className="chg" key={i}>
          <h3>{c.area}</h3>
          <div className="t">{c.text}</div>
          <span className={`pill ${TONE[c.tone]?.[0] || 'p-plain'}`}>{TONE[c.tone]?.[1] || 'Update'}</span>
        </div>
      ))}
    </div>
  )
}

function deltaLabel(d, v) {
  if (v === 'C') return <span className="delta flat">current</span>
  if (v === 'U') return <span className="delta flat">unavailable</span>
  if (d === undefined) return null
  if (d === 'C') return <span className="delta up">now current</span>
  if (d === 'U') return <span className="delta down">now unavailable</span>
  if (typeof d === 'string') return <span className="delta up">changed</span>
  if (d === 0) return <span className="delta flat">no change</span>
  const m = Math.abs(d)
  const txt = m < 1 ? `${Math.round(m * 30.4)} days` : `${m} mo`
  return d > 0 ? <span className="delta up">▲ {txt}</span> : <span className="delta down">▼ {txt}</span>
}

export function VisaBulletin({ data }) {
  const [chart, setChart] = useState('fad')
  const [kind, setKind] = useState('eb')
  if (!data) return <section className="card"><h2>Visa Bulletin</h2><Unavailable what="The Visa Bulletin" /></section>
  const rows = data.charts[kind][chart]
  return (
    <section className="card" aria-labelledby="vbH">
      <div className="card-hd">
        <div>
          <h2 id="vbH">Visa Bulletin · {monthLabel(data.month)}</h2>
          <div className="src">{data.previous_month ? `Change vs ${monthLabel(data.previous_month)} · ` : ''}<a href={data.url || data.meta?.source_url} target="_blank" rel="noopener">travel.state.gov</a> · updated {ago(data.meta?.generated_at)}</div>
        </div>
        <div className="ctrls">
          <Seg label="Chart" value={chart} onChange={setChart} options={[['fad', 'Final action'], ['dff', 'Dates for filing']]} />
          <Seg label="Category" value={kind} onChange={setKind} options={[['eb', 'Employment'], ['fb', 'Family']]} />
        </div>
      </div>
      <div className="tablewrap"><table>
        <thead><tr><th>Category</th>{COUNTRIES.map(([k, l]) => <th key={k}>{l}</th>)}</tr></thead>
        <tbody>{Object.entries(rows).map(([cat, vals]) => (
          <tr key={cat}><td><b>{cat}</b></td>{COUNTRIES.map(([k]) => {
            const v = vals[k]
            return <td key={k}><div className="mv"><span className={`dt ${v === 'C' ? 'cur' : ''}`}>{v ? fmtVB(v) : '—'}</span>{deltaLabel(data.deltas?.[`${kind}.${chart}.${cat}.${k}`], v)}</div></td>
          })}</tr>
        ))}</tbody>
      </table></div>
      <div className="small muted">C means current: no wait. U means unavailable. Final action dates decide when a green card can be approved. Dates for filing decide when you can submit, if USCIS says to use that chart this month.</div>
    </section>
  )
}

export function ProcessingTimes({ data }) {
  const [q, setQ] = useState('')
  if (!data) return <section className="card"><h2>USCIS processing times</h2><Unavailable what="Processing time data" /></section>
  const s = q.trim().toLowerCase()
  const forms = data.forms.filter(f => !s || `${f.form} ${f.label}`.toLowerCase().includes(s))
  return (
    <section className="card" aria-labelledby="ptH">
      <div className="card-hd">
        <div><h2 id="ptH">USCIS processing times</h2>
          <div className="src">Range across offices for 80% of cases · <a href="https://egov.uscis.gov/processing-times/" target="_blank" rel="noopener">egov.uscis.gov</a> via <a href={data.release?.url} target="_blank" rel="noopener">jzebedee/uscis</a> · updated {ago(data.meta?.generated_at)}</div></div>
        <div className="field" style={{ maxWidth: 220 }}><label htmlFor="ptq">Find a form</label><input id="ptq" value={q} onChange={e => setQ(e.target.value)} placeholder="I-485 or work permit" /></div>
      </div>
      <div className="tablewrap"><table>
        <thead><tr><th>Form</th><th>What it's for</th><th className="num">Range</th><th className="num">{data.compared_to ? `vs ${fmt(parse(data.compared_to))}` : 'Change'}</th></tr></thead>
        <tbody>{forms.length ? forms.map(f => {
          const d = data.deltas?.[f.form]
          return (
            <tr key={f.form}><td><b>{f.form}</b></td><td className="wrap">{f.label}</td>
              <td className="num">{f.low_months}–{f.high_months} mo</td>
              <td className="num">{d === undefined ? '—' : <span className={`delta ${d < 0 ? 'up' : d > 0 ? 'down' : 'flat'}`}>{d < 0 ? `${-d} mo faster` : d > 0 ? `${d} mo slower` : 'same'}</span>}</td></tr>
          )
        }) : <tr><td colSpan="4" className="muted">No form matches "{q}".</td></tr>}</tbody>
      </table></div>
    </section>
  )
}

export function Dol({ data }) {
  if (!data) return <section className="card"><h2>Department of Labor</h2><Unavailable what="DOL processing data" /></section>
  return (
    <section className="card" aria-labelledby="dolH">
      <div><h2 id="dolH">Department of Labor</h2>
        <div className="src">PERM and prevailing wage{data.as_of ? ` · as of ${data.as_of}` : ''} · <a href={data.url} target="_blank" rel="noopener">flag.dol.gov</a> · updated {ago(data.meta?.generated_at)}</div></div>
      {data.tables.slice(0, 4).map((t, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {t.heading && <h3>{t.heading}</h3>}
          <div className="tablewrap"><table>
            <thead><tr>{t.header.map((h, j) => <th key={j}>{h}</th>)}</tr></thead>
            <tbody>{t.rows.map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}>{c}</td>)}</tr>)}</tbody>
          </table></div>
        </div>
      ))}
    </section>
  )
}

const WT_TYPES = [['h_next', 'Work (H, L, O, P, Q)'], ['f_next', 'Student (F, M, J)'], ['b_next', 'Visitor (B1/B2)']]

export function WaitTimes({ data }) {
  const [type, setType] = useState('h_next')
  const [q, setQ] = useState('')
  const [all, setAll] = useState(false)
  const rows = useMemo(() => {
    if (!data) return []
    const s = q.trim().toLowerCase()
    return data.posts.filter(p => !s || p.post_raw.toLowerCase().includes(s))
      .map(p => ({ ...p, v: p[type] })).filter(p => p.v && p.v.days !== null && p.v.days !== undefined)
      .sort((a, b) => b.v.days - a.v.days)
  }, [data, type, q])
  if (!data) return <section className="card"><h2>Visa appointment wait times</h2><Unavailable what="Wait time data" /></section>
  const shown = all || q ? rows : rows.slice(0, 12)
  const max = Math.max(1, ...rows.map(r => r.v.days))
  return (
    <section className="card" aria-labelledby="wtH">
      <div className="card-hd">
        <div><h2 id="wtH">Visa appointment wait times</h2>
          <div className="src">Next available interview at each US embassy or consulate · <a href={data.url} target="_blank" rel="noopener">travel.state.gov</a> · updated {ago(data.meta?.generated_at)}</div></div>
        <div className="ctrls">
          <Seg label="Visa type" value={type} onChange={setType} options={WT_TYPES} />
          <div className="field" style={{ maxWidth: 200 }}><label htmlFor="wtq">Find a city</label><input id="wtq" value={q} onChange={e => setQ(e.target.value)} placeholder="Chennai" /></div>
        </div>
      </div>
      <div className="tablewrap"><table>
        <thead><tr><th>Embassy or consulate</th><th className="num">Wait</th><th style={{ width: '40%' }}></th><th className="num">Change</th></tr></thead>
        <tbody>{shown.length ? shown.map(p => {
          const d = data.deltas?.[`${p.post}.${type}`]
          return (
            <tr key={p.post_raw}><td><b>{p.post_raw}</b></td><td className="num">{p.v.text}</td>
              <td><div className="bar" aria-hidden="true"><div className={`fill ${p.v.days > 180 ? 'long' : ''}`} style={{ width: `${(p.v.days / max) * 100}%` }} /></div></td>
              <td className="num">{d ? <span className={`delta ${d > 0 ? 'down' : 'up'}`}>{d > 0 ? '+' : '−'}{Math.abs(d)} days</span> : <span className="delta flat">—</span>}</td></tr>
          )
        }) : <tr><td colSpan="4" className="muted">No consulate matches "{q}" for this visa type.</td></tr>}</tbody>
      </table></div>
      <div className="row small muted" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'space-between' }}>
        <span>Estimates for applicants who need an in-person interview. Actual availability in the booking system changes daily.</span>
        {!q && rows.length > 12 && <button className="linkbtn" onClick={() => setAll(!all)}>{all ? 'Show top 12' : `Show all ${rows.length}`}</button>}
      </div>
    </section>
  )
}
