'use client';

import { useState } from 'react';
import type { TrendPoint } from '@/lib/types';

const SERIES: { type: 'house' | 'apartment'; label: string; cssVar: string }[] = [
  { type: 'house', label: 'Houses', cssVar: 'var(--series-1)' },
  { type: 'apartment', label: 'Apartments', cssVar: 'var(--series-2)' },
];

const W = 380;
const H = 160;
const PAD = { l: 44, r: 70, t: 10, b: 22 };

export function TrendChart({ trends }: { trends: TrendPoint[] }) {
  const [hover, setHover] = useState<{ x: number; year: number } | null>(null);
  if (trends.length < 2) return null;

  const years = [...new Set(trends.map((t) => t.year))].sort();
  const values = trends.map((t) => t.median);
  const yMin = Math.min(...values) * 0.9;
  const yMax = Math.max(...values) * 1.05;
  const x = (year: number) =>
    PAD.l + ((year - years[0]) / Math.max(1, years[years.length - 1] - years[0])) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.t - PAD.b);

  const seriesData = SERIES.map((s) => ({
    ...s,
    points: years
      .map((yr) => trends.find((t) => t.type === s.type && t.year === yr))
      .filter((p): p is TrendPoint => !!p),
  })).filter((s) => s.points.length >= 2);

  const gridVals = [yMin + (yMax - yMin) * 0.25, yMin + (yMax - yMin) * 0.75];

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * W;
    let best = years[0];
    for (const yr of years) if (Math.abs(x(yr) - mx) < Math.abs(x(best) - mx)) best = yr;
    setHover({ x: x(best), year: best });
  };

  return (
    <div className="chart-surface">
      <div className="chart-title">Official sale prices (DVF), median €/m²</div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {gridVals.map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="var(--grid)" strokeWidth={1} />
            <text x={PAD.l - 6} y={y(v) + 3} textAnchor="end" fontSize={9} fill="var(--text-muted)">
              {Math.round(v / 100) / 10}k
            </text>
          </g>
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} stroke="var(--baseline)" strokeWidth={1} />
        {[years[0], years[years.length - 1]].map((yr) => (
          <text key={yr} x={x(yr)} y={H - 8} textAnchor="middle" fontSize={9} fill="var(--text-muted)">
            {yr}
          </text>
        ))}
        {hover && (
          <line x1={hover.x} x2={hover.x} y1={PAD.t} y2={H - PAD.b} stroke="var(--baseline)" strokeWidth={1} strokeDasharray="3 3" />
        )}
        {seriesData.map((s) => (
          <g key={s.type}>
            <polyline
              fill="none"
              stroke={s.cssVar}
              strokeWidth={2}
              strokeLinejoin="round"
              points={s.points.map((p) => `${x(p.year)},${y(p.median)}`).join(' ')}
            />
            {s.points.map((p) => (
              <circle
                key={p.year}
                cx={x(p.year)}
                cy={y(p.median)}
                r={hover?.year === p.year ? 4 : 2.5}
                fill={s.cssVar}
                stroke="var(--surface-1)"
                strokeWidth={hover?.year === p.year ? 2 : 0}
              />
            ))}
            <text
              x={x(s.points[s.points.length - 1].year) + 6}
              y={y(s.points[s.points.length - 1].median) + 3}
              fontSize={10}
              fill="var(--text-secondary)"
            >
              {hover
                ? `€${(s.points.find((p) => p.year === hover.year)?.median ?? s.points[s.points.length - 1].median).toLocaleString()}`
                : s.label}
            </text>
          </g>
        ))}
        {hover && (
          <text x={hover.x} y={PAD.t + 8} textAnchor="middle" fontSize={9} fill="var(--text-muted)">
            {hover.year}
          </text>
        )}
      </svg>
      <div className="legend">
        {seriesData.map((s) => (
          <span key={s.type}>
            <span className="swatch" style={{ background: s.cssVar }} />
            {s.label}
          </span>
        ))}
        <span style={{ color: 'var(--text-muted)' }}>source: DVF (DGFiP)</span>
      </div>
    </div>
  );
}
