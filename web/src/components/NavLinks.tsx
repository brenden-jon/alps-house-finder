'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { loadData } from '@/lib/data';

export function NavLinks() {
  const path = usePathname();
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);

  useEffect(() => {
    loadData().then((d) => setGeneratedAt(d.meta.generatedAt));
  }, []);

  const links = [
    { href: '/', label: 'Ranking' },
    { href: '/map/', label: 'Map' },
    { href: '/communes/', label: 'Communes' },
  ];
  return (
    <>
      {links.map((l) => (
        <Link key={l.href} href={l.href} className={path === l.href ? 'active' : ''}>
          {l.label}
        </Link>
      ))}
      <span className="meta">
        {generatedAt ? `data: ${new Date(generatedAt).toLocaleString()}` : ''}
      </span>
    </>
  );
}
