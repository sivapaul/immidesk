import React, { useEffect, useState } from 'react'
import { loadJSON, monthLabel, today, MON } from './lib.js'
import { Changes, VisaBulletin, ProcessingTimes, Dol, WaitTimes } from './sections/Data.jsx'
import { Deadlines, News } from './sections/News.jsx'
import { Tools } from './sections/Tools.jsx'
import { Footer } from './sections/Footer.jsx'

const FILES = { vb: 'visa_bulletin/latest.json', pt: 'processing_times/latest.json', wt: 'wait_times/latest.json', dol: 'dol/latest.json',
  news: 'news.json', deadlines: 'deadlines.json', changes: 'changes.json', status: 'status.json' }

export default function App() {
  const [d, setD] = useState(null)
  useEffect(() => {
    Promise.all(Object.entries(FILES).map(async ([k, p]) => [k, await loadJSON(p)])).then(e => setD(Object.fromEntries(e)))
  }, [])
  if (!d) return <div className="wrap" style={{ paddingBlock: 40 }}>Loading the latest data…</div>
  const sample = Object.values(d).some(x => x?.meta?.sample)
  const t = today()
  return (
    <>
      {sample && <div className="samplebar"><div className="wrap">Sample data for development. Run the pipeline to load live figures. Not legal advice.</div></div>}
      <header><div className="wrap">
        <div className="brand"><h1>ImmiDesk</h1><span className="tagline">US immigration data from official sources, on one page</span></div>
        {d.vb && <span className="small muted">Visa Bulletin: {monthLabel(d.vb.month)}</span>}
      </div></header>
      <main className="wrap pub">
        <div className="lead">
          <h2>This month in US immigration · {MON[t.getMonth()]} {t.getFullYear()}</h2>
          <p className="muted">What moved across the Visa Bulletin, USCIS, the Department of Labor and consulates, plus new rules and the dates that matter. Updated automatically. No account needed.</p>
        </div>
        <Changes data={d.changes} />
        <VisaBulletin data={d.vb} />
        <div className="grid2">
          <Deadlines data={d.deadlines} />
          <div className="col"><Tools vb={d.vb} /></div>
        </div>
        <div className="grid2">
          <ProcessingTimes data={d.pt} />
          <div className="col"><Dol data={d.dol} /></div>
        </div>
        <WaitTimes data={d.wt} />
        <News data={d.news} />
      </main>
      <Footer status={d.status} />
    </>
  )
}
