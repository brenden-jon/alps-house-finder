'use client';

import { useEffect } from 'react';
import { fmtEur } from '@/lib/data';
import type { Commune, Listing } from '@/lib/types';
import { TrendChart } from './TrendChart';

export function ListingDetail({
  listing: l,
  commune,
  weights,
  dimensions,
  onClose,
}: {
  listing: Listing;
  commune: Commune | null;
  weights: Record<string, number>;
  dimensions: { key: string; label: string }[];
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const licenseRisky = (commune?.ratings.licenseRisk ?? 10) <= 4;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="detail" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose} aria-label="Close">
          ✕
        </button>
        <h2>{l.title || `${l.type} in ${commune?.name ?? l.communeRaw}`}</h2>
        <div className="commune-line" style={{ color: 'var(--text-secondary)' }}>
          {commune?.name ?? l.communeRaw} · {l.type} · {l.area ? `${Math.round(l.area)} m²` : '? m²'} ·{' '}
          {l.bedrooms != null ? `${l.bedrooms} bedrooms` : `${l.rooms ?? '?'} rooms`}
          {l.dpe ? ` · DPE ${l.dpe}` : ''} · first seen {l.firstSeen}
        </div>
        <div className="price-line" style={{ margin: '8px 0' }}>
          <span className="price" style={{ fontSize: 20 }}>
            {fmtEur(l.price)}
          </span>
          {l.renovCost > 0 && (
            <span className="all-in">
              + ~{fmtEur(l.renovCost)} renovation ({l.renovFlag}) = <b>{fmtEur(l.allIn)} all-in</b>
            </span>
          )}
        </div>

        {l.photos.length > 0 && (
          <div className="gallery">
            {l.photos.map((p) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={p}
                src={p}
                alt=""
                loading="lazy"
                referrerPolicy="no-referrer"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            ))}
          </div>
        )}

        <div className="grid2">
          <div>
            <h4>Score breakdown</h4>
            <div className="dims">
              {dimensions.map((d) => {
                const ds = l.scores[d.key];
                if (!ds) return null;
                return (
                  <div className="dim-row" key={d.key} title={ds.d ?? ''}>
                    <span>
                      {d.label} <span style={{ color: 'var(--text-muted)' }}>×{weights[d.key] ?? 1}</span>
                    </span>
                    <div className="bar">
                      <div style={{ width: `${ds.s * 100}%` }} />
                    </div>
                    <span className="num">{ds.s.toFixed(2)}</span>
                  </div>
                );
              })}
            </div>
            <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 6 }}>
              Hover a row for the reasoning. Renovation costs are keyword-based estimates, not quotes.
            </p>

            <h4>Sources</h4>
            <div className="source-links">
              {l.sources.map((s) => (
                <a key={s.code + s.url} href={s.url} target="_blank" rel="noreferrer">
                  {s.name}
                  {s.agency ? ` — ${s.agency}` : ''} ↗{!s.active && ' (no longer listed)'}
                </a>
              ))}
            </div>

            {l.priceHistory.length > 1 && (
              <>
                <h4>Price history</h4>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  {l.priceHistory.map(([d, p]) => (
                    <div key={d + p}>
                      {d}: {fmtEur(p)}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
          <div>
            {commune && (
              <>
                <h4>Tourism license — {commune.name}</h4>
                <div className={`note-box ${licenseRisky ? 'warn' : ''}`}>
                  {licenseRisky && <b>⚠ License risk — </b>}
                  {commune.licenseNotes || 'No notes.'}
                </div>
                <h4>Rental market</h4>
                <div className="note-box">
                  {commune.rentalNotes || 'No notes.'}{' '}
                  {commune.weeklyWinter &&
                    `~€${commune.weeklyWinter}/wk winter, €${commune.weeklySummer}/wk summer, ~${commune.occupancyWeeks} weeks/yr.`}
                </div>
                <h4>Price trend</h4>
                <TrendChart trends={commune.trends} />
              </>
            )}
            <h4>Description</h4>
            <div className="desc">{l.description || '—'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
