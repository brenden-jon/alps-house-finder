'use client';

import dynamic from 'next/dynamic';

const MapView = dynamic(() => import('@/components/MapView').then((m) => m.MapView), {
  ssr: false,
  loading: () => <div className="empty-state">Loading map…</div>,
});

export default function MapPage() {
  return (
    <div className="map-wrap">
      <MapView />
    </div>
  );
}
