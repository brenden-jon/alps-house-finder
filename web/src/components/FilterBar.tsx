'use client';

import type { Commune } from '@/lib/types';
import type { UiFilters } from '@/lib/scoring';

const TYPES = ['house', 'chalet', 'farmhouse', 'apartment'];

export function FilterBar({
  filters,
  communes,
  onChange,
}: {
  filters: UiFilters;
  communes: Commune[];
  onChange: (f: UiFilters) => void;
}) {
  const set = (patch: Partial<UiFilters>) => onChange({ ...filters, ...patch });

  return (
    <div>
      <div className="filter-row">
        <label>Max all-in price (€, incl. renovation estimate)</label>
        <input
          type="number"
          step={25000}
          value={filters.maxAllIn}
          onChange={(e) => set({ maxAllIn: Number(e.target.value) || 0 })}
        />
      </div>
      <div className="filter-row">
        <label>Min bedrooms</label>
        <input
          type="number"
          min={0}
          max={10}
          value={filters.minBedrooms}
          onChange={(e) => set({ minBedrooms: Number(e.target.value) || 0 })}
        />
      </div>
      <div className="filter-row">
        <label>Min area (m²)</label>
        <input
          type="number"
          min={0}
          step={10}
          value={filters.minArea}
          onChange={(e) => set({ minArea: Number(e.target.value) || 0 })}
        />
      </div>
      <div className="filter-row">
        <label>Property types</label>
        {TYPES.map((t) => (
          <span className="check" key={t}>
            <input
              type="checkbox"
              id={`type-${t}`}
              checked={filters.types.includes(t)}
              onChange={(e) =>
                set({
                  types: e.target.checked
                    ? [...filters.types, t]
                    : filters.types.filter((x) => x !== t),
                })
              }
            />
            <label htmlFor={`type-${t}`} style={{ margin: 0 }}>
              {t}
            </label>
          </span>
        ))}
      </div>
      <div className="filter-row">
        <label>Communes (none selected = all)</label>
        <div className="commune-chips">
          {communes.map((c) => (
            <button
              key={c.insee}
              className={`chip ${filters.communes.includes(c.insee) ? 'on' : ''}`}
              onClick={() =>
                set({
                  communes: filters.communes.includes(c.insee)
                    ? filters.communes.filter((x) => x !== c.insee)
                    : [...filters.communes, c.insee],
                })
              }
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>
      <div className="filter-row">
        <span className="check">
          <input
            type="checkbox"
            id="hide-heavy"
            checked={filters.hideHeavyRenovation}
            onChange={(e) => set({ hideHeavyRenovation: e.target.checked })}
          />
          <label htmlFor="hide-heavy" style={{ margin: 0 }}>
            Hide heavy renovations
          </label>
        </span>
        <span className="check">
          <input
            type="checkbox"
            id="only-starred"
            checked={filters.onlyStarred}
            onChange={(e) => set({ onlyStarred: e.target.checked })}
          />
          <label htmlFor="only-starred" style={{ margin: 0 }}>
            Only starred ★
          </label>
        </span>
      </div>
      <div className="filter-row">
        <label>Search text</label>
        <input
          type="text"
          placeholder="e.g. sauna, vue, garage"
          value={filters.search}
          onChange={(e) => set({ search: e.target.value })}
        />
      </div>
    </div>
  );
}
