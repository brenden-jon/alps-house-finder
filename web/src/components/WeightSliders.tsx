'use client';

import { DIMENSIONS } from '@/lib/types';

export function WeightSliders({
  weights,
  defaults,
  onChange,
}: {
  weights: Record<string, number>;
  defaults: Record<string, number>;
  onChange: (w: Record<string, number>) => void;
}) {
  return (
    <div>
      {DIMENSIONS.map((d) => (
        <div className="slider-row" key={d.key}>
          <span>{d.label}</span>
          <input
            type="range"
            min={0}
            max={2}
            step={0.25}
            value={weights[d.key] ?? 1}
            onChange={(e) => onChange({ ...weights, [d.key]: Number(e.target.value) })}
          />
          <span className="val">{(weights[d.key] ?? 1).toFixed(2).replace(/\.?0+$/, '')}</span>
        </div>
      ))}
      <button className="ghost-btn" style={{ marginTop: 8 }} onClick={() => onChange({ ...defaults })}>
        Reset weights
      </button>
    </div>
  );
}
