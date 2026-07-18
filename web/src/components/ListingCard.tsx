'use client';

import { fmtEur } from '@/lib/data';
import type { FinanceResult } from '@/lib/scoring';
import type { Listing } from '@/lib/types';

export function ListingCard({
  listing: l,
  rank,
  score,
  finance,
  communeName,
  starred,
  onOpen,
  onStar,
  onHide,
}: {
  listing: Listing;
  rank: number;
  score: number;
  finance?: FinanceResult;
  communeName: string;
  starred: boolean;
  onOpen: () => void;
  onStar: () => void;
  onHide: () => void;
}) {
  const priceDropped =
    l.priceHistory.length >= 2 &&
    l.priceHistory[l.priceHistory.length - 1][1] < l.priceHistory[0][1];

  const isNew = Date.now() - new Date(l.firstSeen).getTime() < 8 * 24 * 3600 * 1000;

  return (
    <div className="card" onClick={onOpen}>
      <div className="photo">
        {l.photos[0] && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={l.photos[0]}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        )}
        <span className="rank-badge">#{rank}</span>
        <span className="score-badge">{score.toFixed(2)}</span>
      </div>
      <div className="body">
        <div className="title">{l.title || `${l.type} in ${communeName}`}</div>
        <div className="commune-line">
          {communeName} · {l.type}
          {l.sources[0]?.agency ? ` · ${l.sources[0].agency}` : ''}
        </div>
        <div className="price-line">
          <span className="price">{fmtEur(l.price)}</span>
          {l.renovCost > 0 && (
            <span className="all-in">
              + ~{fmtEur(l.renovCost)} works = {fmtEur(l.allIn)} all-in
            </span>
          )}
        </div>
        <div className="facts">
          {l.area ? <span>{Math.round(l.area)} m²</span> : <span>? m²</span>}
          <span>{l.bedrooms != null ? `${l.bedrooms} bd` : `${l.rooms ?? '?'} rooms`}</span>
          {l.dpe && <span>DPE {l.dpe}</span>}
          {l.land ? <span>{Math.round(l.land)} m² land</span> : null}
        </div>
        {finance && (
          <div
            className="facts"
            title={`Equity in: ${fmtEur(Math.round(finance.equity))} · gross rent ~${fmtEur(Math.round(finance.grossRevenue))}/yr · mortgage ${fmtEur(Math.round(finance.debtService))}/yr · return on equity incl. amortization ${(finance.roe * 100).toFixed(1)}%`}
          >
            <span style={{ color: finance.cashflow >= 0 ? 'var(--good-text)' : 'var(--critical)' }}>
              {finance.cashflow >= 0 ? '+' : '−'}
              {fmtEur(Math.abs(Math.round(finance.cashflow)))}/yr cashflow
            </span>
            <span>RoE {(finance.roe * 100).toFixed(1)}%</span>
            <span>{fmtEur(Math.round(finance.equity))} cash in</span>
          </div>
        )}
        <div className="flags">
          {isNew && <span className="badge drop">new</span>}
          {priceDropped && <span className="badge drop">price ↓</span>}
          {l.renovFlag === 'heavy' && <span className="badge warn">heavy renovation</span>}
          {l.dpe === 'G' && <span className="badge crit">DPE G — rental ban</span>}
          {l.bedrooms == null && <span className="badge">bedrooms unknown</span>}
        </div>
        <div className="actions" onClick={(e) => e.stopPropagation()}>
          <button className={`icon-btn ${starred ? 'on' : ''}`} onClick={onStar} title="Star">
            ★
          </button>
          <button className="icon-btn" onClick={onHide} title="Hide from ranking">
            ✕
          </button>
          {l.sources.map((s) => (
            <a key={s.code + s.url} href={s.url} target="_blank" rel="noreferrer" className="icon-btn">
              {s.name} ↗
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
