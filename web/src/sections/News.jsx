import React, { useMemo, useState } from 'react'
import { TOPICS, KIND_LABEL, CONFIDENCE, parse, today, daysBetween, fmt, fmtShort, ago } from '../lib.js'

function TopicChips({ value, onChange, counts }) {
  return (
    <div className="chips" role="group" aria-label="Topic">
      {TOPICS.filter(([k]) => k === 'all' || counts[k]).map(([k, l]) => (
        <button key={k} aria-pressed={value === k} onClick={() => onChange(k)}>{l}{k !== 'all' ? ` ${counts[k]}` : ''}</button>
      ))}
    </div>
  )
}

const countTags = list => list.reduce((acc, x) => { (x.tags || []).forEach(t => { acc[t] = (acc[t] || 0) + 1 }); return acc }, {})

export function Deadlines({ data }) {
  const [topic, setTopic] = useState('all')
  const [past, setPast] = useState(false)
  const t = today()
  const items = data?.items || []
  const filtered = items.filter(d => topic === 'all' || (d.tags || []).includes(topic))
  const upcoming = filtered.filter(d => parse(d.date) >= t)
  const recent = filtered.filter(d => parse(d.date) < t).reverse()
  const list = past ? recent : upcoming.slice(0, 10)
  return (
    <section className="card" aria-labelledby="dlH">
      <div className="card-hd">
        <div><h2 id="dlH">Dates to know</h2><div className="src">Comment deadlines, effective dates and filing windows pulled from rules and news · updated {ago(data?.meta?.generated_at)}</div></div>
        <div className="seg" role="group" aria-label="When">
          <button aria-pressed={!past} onClick={() => setPast(false)}>Upcoming</button>
          <button aria-pressed={past} onClick={() => setPast(true)}>Last 30 days</button>
        </div>
      </div>
      <TopicChips value={topic} onChange={setTopic} counts={countTags(items)} />
      <div>
        {list.length ? list.map((d, i) => {
          const date = parse(d.date), n = daysBetween(t, date)
          const [cl, cc] = CONFIDENCE[d.confidence] || ['', 'p-plain']
          return (
            <div className="dl" key={`${d.date}-${d.item_id}-${i}`}>
              <div className="when">{fmtShort(date)} {date.getFullYear() !== t.getFullYear() ? date.getFullYear() : ''}<span>{n === 0 ? 'today' : n > 0 ? `in ${n} days` : `${-n} days ago`}</span></div>
              <div>
                <div className="t">{d.item_id ? <>{d.label}: <a href={d.url} target="_blank" rel="noopener">{d.title}</a></> : d.url ? <a href={d.url} target="_blank" rel="noopener">{d.title}</a> : d.title}</div>
                <div className="meta"><span className={`pill ${cc}`}>{cl}</span><span>{d.source}</span></div>
              </div>
            </div>
          )
        }) : <div className="empty">{past ? 'Nothing in the last 30 days for this topic.' : 'No upcoming dates for this topic.'}</div>}
      </div>
    </section>
  )
}

export function News({ data }) {
  const [topic, setTopic] = useState('all')
  const [q, setQ] = useState('')
  const [limit, setLimit] = useState(15)
  const items = data?.items || []
  const counts = useMemo(() => countTags(items), [items])
  const s = q.trim().toLowerCase()
  const filtered = items.filter(i => (topic === 'all' || i.tags.includes(topic)) && (!s || `${i.title} ${i.summary}`.toLowerCase().includes(s)))
  return (
    <section className="card" aria-labelledby="nwH">
      <div className="card-hd">
        <div><h2 id="nwH">News and rule changes</h2><div className="src">Federal Register, USCIS, State Dept, DHS, DOL, CBP, SEVP, White House and embassies · updated {ago(data?.meta?.generated_at)}</div></div>
        <div className="field" style={{ maxWidth: 240 }}><label htmlFor="nq">Search news</label><input id="nq" value={q} onChange={e => setQ(e.target.value)} placeholder="OPT, fee, H-4…" /></div>
      </div>
      <TopicChips value={topic} onChange={setTopic} counts={counts} />
      <div className="news">
        {filtered.slice(0, limit).map(i => {
          const next = (i.deadlines || []).map(d => ({ ...d, dt: parse(d.date) })).filter(d => d.dt >= today()).sort((a, b) => a.dt - b.dt)[0]
          return (
            <article className="ni" key={i.id}>
              <div className="top">
                <span className={`pill ${/rule|presidential/.test(i.kind) ? 'p-info' : 'p-plain'}`}>{KIND_LABEL[i.kind] || i.kind}</span>
                <span>{fmt(parse(i.published))}</span>
                {next && <span className="pill p-warn">{next.label} {fmt(next.dt)}</span>}
              </div>
              <div className="t"><a href={i.sources[0].url} target="_blank" rel="noopener">{i.title}</a></div>
              {i.summary && <div className="s">{i.summary}</div>}
              <div className="srcs">{i.sources.map((src, k) => <a key={k} href={src.url} target="_blank" rel="noopener">{src.name}</a>)}</div>
            </article>
          )
        })}
        {!filtered.length && <div className="empty">No news matches this filter.</div>}
      </div>
      {filtered.length > limit && <button className="linkbtn" onClick={() => setLimit(limit + 20)}>Show more ({filtered.length - limit} left)</button>}
    </section>
  )
}
