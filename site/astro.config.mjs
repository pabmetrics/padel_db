import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://padeldb.es',
  integrations: [sitemap()],
  build: { format: 'directory' },
});
