import type { Metadata } from 'next';
import './globals.css';
import { NavLinks } from '@/components/NavLinks';

export const metadata: Metadata = {
  title: 'Alps House Finder',
  description: 'Ranked French Alps property listings for the crew',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="topnav">
          <h1>🏔 Alps House Finder</h1>
          <NavLinks />
        </nav>
        {children}
      </body>
    </html>
  );
}
