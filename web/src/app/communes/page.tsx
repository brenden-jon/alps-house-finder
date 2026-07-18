'use client';

import { Fragment, useEffect, useState } from 'react';
import { loadData } from '@/lib/data';
import type { Commune } from '@/lib/types';
import { TrendChart } from '@/components/TrendChart';

export default function CommunesPage() {
  const [communes, setCommunes] = useState<Commune[]>([]);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    loadData().then((d) => setCommunes(d.communes));
  }, []);

  return (
    <main className="content" style={{ maxWidth: 1100, margin: '0 auto' }}>
      <p style={{ color: 'var(--text-muted)', margin: '8px 0 14px', fontSize: 13 }}>
        The curated knowledge base behind commune-level scores. Ratings are 0–10 judgment calls
        with notes; license facts move quarterly — check the updated date.
      </p>
      <table className="communes-table">
        <thead>
          <tr>
            <th>Commune</th>
            <th>Resort</th>
            <th>Top alt</th>
            <th>GVA</th>
            <th>Ski</th>
            <th>BC</th>
            <th>Summer</th>
            <th>Charm</th>
            <th>Village life</th>
            <th>License safety</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {communes.map((c) => (
            <Fragment key={c.insee}>
              <tr
                onClick={() => setOpen(open === c.insee ? null : c.insee)}
                style={{ cursor: 'pointer' }}
              >
                <td>
                  <b>{c.name}</b> ({c.dept})
                </td>
                <td>{c.resort}</td>
                <td className="num">{c.topAlt} m</td>
                <td className="num">{c.genevaMin} min</td>
                <td className="num">{c.ratings.ski}</td>
                <td className="num">{c.ratings.backcountry}</td>
                <td className="num">{c.ratings.summer}</td>
                <td className="num">{c.ratings.charm}</td>
                <td className="num">{c.ratings.villageLife}</td>
                <td className="num">{c.ratings.licenseRisk}</td>
                <td>{c.updatedAt}</td>
              </tr>
              {open === c.insee && (
                <tr>
                  <td colSpan={11}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, padding: '6px 0 12px' }}>
                      <div>
                        <div className="note-box warn" style={{ marginBottom: 10 }}>
                          <b>License:</b> {c.licenseNotes || '—'}
                        </div>
                        <div className="note-box" style={{ marginBottom: 10 }}>
                          <b>Slopes:</b> {c.slopeNotes || '—'}
                        </div>
                        <div className="note-box">
                          <b>Rental:</b> {c.rentalNotes || '—'}{' '}
                          {c.weeklyWinter &&
                            `~€${c.weeklyWinter}/wk winter, €${c.weeklySummer}/wk summer, ~${c.occupancyWeeks} wks/yr.`}
                        </div>
                      </div>
                      <TrendChart trends={c.trends} />
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </main>
  );
}
