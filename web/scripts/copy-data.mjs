// Copy data/export/*.json into web/public/data/ so the static site can fetch it.
import { cpSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(here, '../../data/export');
const dst = path.resolve(here, '../public/data');

if (!existsSync(src)) {
  console.error(`No export data at ${src} — run \`alpsfinder export\` first.`);
  process.exit(1);
}
mkdirSync(dst, { recursive: true });
cpSync(src, dst, { recursive: true });
console.log(`Copied export data -> ${dst}`);
