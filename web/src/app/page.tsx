'use client';

import { useEffect, useMemo, useState } from 'react';
import { loadData, type AppData } from '@/lib/data';
import {
  computeFinance,
  defaultUiFilters,
  loadIdSet,
  loadWeights,
  passesFilters,
  saveIdSet,
  saveWeights,
  totalScore,
  type UiFilters,
} from '@/lib/scoring';
import { DIMENSIONS, type Listing } from '@/lib/types';
import { WeightSliders } from '@/components/WeightSliders';
import { FilterBar } from '@/components/FilterBar';
import { ListingCard } from '@/components/ListingCard';
import { ListingDetail } from '@/components/ListingDetail';

export default function RankingPage() {
  const [data, setData] = useState<AppData | null>(null);
  const [weights, setWeights] = useState<Record<string, number> | null>(null);
  const [filters, setFilters] = useState<UiFilters | null>(null);
  const [starred, setStarred] = useState<Set<number>>(new Set());
  const [hidden, setHidden] = useState<Set<number>>(new Set());
  const [openId, setOpenId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<'score' | 'econ'>('score');
  const [onlyPositive, setOnlyPositive] = useState(false);

  useEffect(() => {
    loadData().then((d) => {
      setData(d);
      setWeights(loadWeights(d.meta.defaultWeights));
      setFilters(defaultUiFilters(d.meta));
      setStarred(loadIdSet('alps.starred'));
      setHidden(loadIdSet('alps.hidden'));
    });
  }, []);

  const ranked = useMemo(() => {
    if (!data || !weights || !filters) return [];
    const byInsee = new Map(data.communes.map((c) => [c.insee, c]));
    return data.listings
      .filter((l) => passesFilters(l, filters, data.meta, starred, hidden))
      .map((l) => ({
        listing: l,
        score: totalScore(l, weights),
        finance: computeFinance(l, byInsee.get(l.commune ?? '') ?? null),
      }))
      .filter((x) => !onlyPositive || x.finance.cashflow > 0)
      .sort((a, b) =>
        sortBy === 'econ' ? b.finance.roe - a.finance.roe : b.score - a.score,
      );
  }, [data, weights, filters, starred, hidden, sortBy, onlyPositive]);

  if (!data || !weights || !filters) {
    return <div className="empty-state">Loading listings…</div>;
  }

  const communeName = (l: Listing) =>
    data.communes.find((c) => c.insee === l.commune)?.name ?? l.communeRaw ?? '?';

  const toggle = (set: Set<number>, id: number) => {
    const next = new Set(set);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  };

  const openListing = openId !== null ? data.listings.find((l) => l.id === openId) : null;

  return (
    <div className="layout">
      <aside className="sidebar">
        <h3>Weights</h3>
        <WeightSliders
          weights={weights}
          defaults={data.meta.defaultWeights}
          onChange={(w) => {
            setWeights(w);
            saveWeights(w);
          }}
        />
        <h3>Filters</h3>
        <FilterBar filters={filters} communes={data.communes} onChange={setFilters} />
      </aside>
      <main className="content">
        <div className="sort-bar">
          <label>
            Sort by{' '}
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as 'score' | 'econ')}>
              <option value="score">Fit score</option>
              <option value="econ">Economic case (return on equity)</option>
            </select>
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={onlyPositive}
              onChange={(e) => setOnlyPositive(e.target.checked)}
            />
            Cashflow-positive only
          </label>
          <span className="model-note">
            Model: 70% LTV, 3.4% / 20 yrs, 7.5% notary, 22% mgmt, 1.2% fixed costs — estimates, not advice
          </span>
        </div>
        {ranked.length === 0 ? (
          <div className="empty-state">No listings pass the current filters.</div>
        ) : (
          <div className="cards">
            {ranked.map(({ listing, score, finance }, i) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                rank={i + 1}
                score={score}
                finance={finance}
                communeName={communeName(listing)}
                starred={starred.has(listing.id)}
                onOpen={() => setOpenId(listing.id)}
                onStar={() => {
                  const next = toggle(starred, listing.id);
                  setStarred(next);
                  saveIdSet('alps.starred', next);
                }}
                onHide={() => {
                  const next = toggle(hidden, listing.id);
                  setHidden(next);
                  saveIdSet('alps.hidden', next);
                }}
              />
            ))}
          </div>
        )}
      </main>
      {openListing && (
        <ListingDetail
          listing={openListing}
          commune={data.communes.find((c) => c.insee === openListing.commune) ?? null}
          weights={weights}
          dimensions={DIMENSIONS}
          onClose={() => setOpenId(null)}
        />
      )}
    </div>
  );
}
