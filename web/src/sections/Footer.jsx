import React from 'react'
import { ago } from '../lib.js'

export function Footer({ status }) {
  const sources = Object.entries(status?.sources || {})
  return (
    <footer><div className="wrap">
      <h3 id="sources">Data sources</h3>
      {sources.length ? (
        <div className="tablewrap status"><table>
          <thead><tr><th>Source</th><th>Status</th><th>Last successful update</th><th>Items</th></tr></thead>
          <tbody>{sources.map(([id, s]) => {
            const stale = s.last_success && s.max_age_hours && (Date.now() - new Date(s.last_success)) / 36e5 > s.max_age_hours
            const pill = !s.ok ? ['p-bad', 'Failing'] : stale ? ['p-warn', 'Stale'] : ['p-ok', 'OK']
            return (
              <tr key={id} title={s.error || ''}>
                <td><a href={s.url} target="_blank" rel="noopener">{s.name}</a></td>
                <td><span className={`pill ${pill[0]}`}>{pill[1]}</span></td>
                <td>{ago(s.last_success)}</td>
                <td className="num">{s.count ?? '—'}</td>
              </tr>
            )
          })}</tbody>
        </table></div>
      ) : <div className="empty">Source status is not available.</div>}
      <div>Processing times come from the daily dataset published by <a href="https://github.com/jzebedee/uscis" target="_blank" rel="noopener">jzebedee/uscis</a>. Media and law firm items show headlines and links only.</div>
      <div>ImmiDesk is an open-source project and is not affiliated with any government agency. It is not legal advice. Always confirm with the official source or an immigration attorney before acting.</div>
    </div></footer>
  )
}
