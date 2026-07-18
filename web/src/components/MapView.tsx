'use client';

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fmtEur, loadData } from '@/lib/data';
import { loadIdSet, loadWeights, totalScore } from '@/lib/scoring';

// score -> sequential blue ramp (ordinal steps 250..700)
function scoreColor(s: number): string {
  if (s >= 0.75) return '#0d366b';
  if (s >= 0.65) return '#1c5cab';
  if (s >= 0.55) return '#3987e5';
  return '#86b6ef';
}

export function MapView() {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = L.map(ref.current).setView([45.95, 6.65], 9);
    mapRef.current = map;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 17,
    }).addTo(map);

    loadData().then(({ listings, communes, meta }) => {
      const weights = loadWeights(meta.defaultWeights);
      const hidden = loadIdSet('alps.hidden');

      for (const c of communes) {
        if (!c.lat || !c.lon) continue;
        L.marker([c.lat, c.lon], {
          icon: L.divIcon({
            className: '',
            html: `<div style="background:var(--surface-1);border:1px solid var(--border);border-radius:6px;padding:1px 6px;font-size:11px;font-weight:600;white-space:nowrap;color:var(--text-secondary)">${c.name}</div>`,
          }),
          interactive: false,
        }).addTo(map);
      }

      for (const l of listings) {
        if (l.status !== 'active' || hidden.has(l.id) || !l.lat || !l.lon) continue;
        const score = totalScore(l, weights);
        // jitter commune-centroid/approx positions so stacked markers stay visible
        const jitter = l.geo === 'exact' ? 0 : 0.004;
        const lat = l.lat + (jitter ? (Math.random() - 0.5) * jitter : 0);
        const lon = l.lon + (jitter ? (Math.random() - 0.5) * jitter : 0);
        const m = L.circleMarker([lat, lon], {
          radius: 8,
          weight: 2,
          color: '#fcfcfb',
          fillColor: scoreColor(score),
          fillOpacity: 0.95,
          dashArray: l.geo === 'exact' ? undefined : '2 3',
        }).addTo(map);
        m.bindPopup(
          `<div style="min-width:190px;font:13px system-ui">
             ${l.photos[0] ? `<img src="${l.photos[0]}" referrerpolicy="no-referrer" style="width:100%;height:90px;object-fit:cover;border-radius:6px" onerror="this.remove()"/>` : ''}
             <div style="font-weight:600;margin-top:4px">${(l.title || l.type).slice(0, 60)}</div>
             <div>${fmtEur(l.price)} · ${l.area ? Math.round(l.area) + ' m²' : ''} · score ${score.toFixed(2)}</div>
             <a href="${l.sources[0]?.url ?? '#'}" target="_blank" rel="noreferrer">open listing ↗</a>
           </div>`,
        );
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div ref={ref} style={{ height: '100%', width: '100%' }} />;
}
