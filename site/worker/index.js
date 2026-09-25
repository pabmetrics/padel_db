// Punto de entrada del Worker padel-db (Cloudflare Workers con assets
// estáticos, ver wrangler.jsonc). La web es dist/ tal cual; el único código
// que corre en el borde es /api/adhoc.
import { atenderGet, atenderPost } from './adhoc.js';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/api/adhoc' || pathname === '/api/adhoc/') {
      if (request.method === 'POST') return atenderPost(request, env);
      if (request.method === 'GET') return atenderGet(request, env);
      return new Response('Método no permitido', { status: 405, headers: { allow: 'GET, POST' } });
    }
    return env.ASSETS.fetch(request);
  },
};
