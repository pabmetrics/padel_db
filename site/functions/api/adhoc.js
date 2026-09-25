// POST https://padeldb.es/api/adhoc — pide un gráfico a medida
// (content/chart_factory/adhoc.py) sin que quien lo pide tenga un token de
// GitHub. Cloudflare Pages Function: se despliega con el propio sitio.
//
// Quien llama (Cowork) solo conoce X-Adhoc-Key, que únicamente sirve para
// pedir un gráfico: el pedido sigue pasando por la validación del workflow y
// por la revisión humana antes de publicarse. El token de GitHub vive solo
// aquí, como secreto del proyecto de Pages.
//
// Configuración en Cloudflare Pages (Settings → Variables and Secrets / Bindings):
//   ADHOC_KEY     secreto: la clave que envía Cowork en X-Adhoc-Key
//   GITHUB_TOKEN  secreto: token fine-grained, solo pabmetrics/padel_db,
//                 permisos Actions: read and write + Contents: read
//   ADHOC_KV      binding KV: contador por hora y log de llamadas
//
// GET con la misma cabecera devuelve las últimas llamadas (auditoría).

const REPO = 'pabmetrics/padel_db';
const WORKFLOW = 'adhoc_chart.yml';
const LIMITE_POR_HORA = 20;
const MAX_BYTES = 4096;
const TIPOS = ['jugadores', 'perfil_top100'];
const DIAS_LOG = 90;

function respuesta(estado, cuerpo) {
  return new Response(JSON.stringify(cuerpo, null, 2), {
    status: estado,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'x-robots-tag': 'noindex, nofollow',
    },
  });
}

async function sha256(texto) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(texto)));
}

// Comparación en tiempo constante sobre los hashes (misma longitud siempre).
export async function claveValida(recibida, esperada) {
  if (!recibida || !esperada) return false;
  const [a, b] = await Promise.all([sha256(recibida), sha256(esperada)]);
  let diferencia = 0;
  for (let i = 0; i < a.length; i++) diferencia |= a[i] ^ b[i];
  return diferencia === 0;
}

// Comprobaciones baratas antes de gastar una ejecución de Actions; la
// validación del contenido (nombres, datos, título) la hace el workflow.
export function validarPedido(texto) {
  if (new TextEncoder().encode(texto).length > MAX_BYTES) {
    return { error: `El pedido supera ${MAX_BYTES} bytes` };
  }
  let pedido;
  try {
    pedido = JSON.parse(texto);
  } catch {
    return { error: 'El cuerpo no es JSON válido' };
  }
  if (!pedido || typeof pedido !== 'object' || Array.isArray(pedido)) {
    return { error: 'El pedido debe ser un objeto JSON' };
  }
  if (!TIPOS.includes(pedido.tipo)) {
    return { error: `'tipo' debe ser uno de: ${TIPOS.join(', ')}` };
  }
  return { pedido };
}

function horaUTC(ahora) {
  return ahora.toISOString().slice(0, 13); // 2026-09-25T16
}

async function registrar(kv, ahora, entrada) {
  // KV lista en orden lexicográfico: con el tiempo invertido, la más
  // reciente sale primero y basta con la primera página.
  const invertido = String(9999999999999 - ahora.getTime()).padStart(13, '0');
  const clave = `log:${invertido}:${crypto.randomUUID().slice(0, 8)}`;
  await kv.put(clave, JSON.stringify({ fecha: ahora.toISOString(), ...entrada }), {
    expirationTtl: DIAS_LOG * 86400,
  });
}

export async function atenderPost(request, env, { fetchFn = fetch, ahora = new Date() } = {}) {
  if (!env.ADHOC_KEY || !env.GITHUB_TOKEN || !env.ADHOC_KV) {
    return respuesta(503, { ok: false, error: 'Endpoint sin configurar (ADHOC_KEY, GITHUB_TOKEN, ADHOC_KV)' });
  }
  if (!(await claveValida(request.headers.get('x-adhoc-key'), env.ADHOC_KEY))) {
    // Sin escribir en KV: un intento sin clave no debe gastar cuota de escritura.
    console.log('adhoc: clave no válida');
    return respuesta(401, { ok: false, error: 'X-Adhoc-Key no válida' });
  }

  const texto = await request.text();
  const { pedido, error } = validarPedido(texto);
  if (error) {
    await registrar(env.ADHOC_KV, ahora, { resultado: 400, motivo: error, pedido: texto.slice(0, 500) });
    return respuesta(400, { ok: false, error });
  }

  const claveHora = `rate:${horaUTC(ahora)}`;
  const usadas = parseInt((await env.ADHOC_KV.get(claveHora)) || '0', 10);
  if (usadas >= LIMITE_POR_HORA) {
    await registrar(env.ADHOC_KV, ahora, { resultado: 429, pedido });
    return respuesta(429, { ok: false, error: `Límite de ${LIMITE_POR_HORA} pedidos por hora alcanzado` });
  }
  await env.ADHOC_KV.put(claveHora, String(usadas + 1), { expirationTtl: 7200 });

  const gh = await fetchFn(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: 'application/vnd.github+json',
      'x-github-api-version': '2022-11-28',
      'user-agent': 'padeldb-adhoc',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ ref: 'main', inputs: { pedido: JSON.stringify(pedido) } }),
  });

  if (gh.status !== 204) {
    const detalle = (await gh.text()).slice(0, 300);
    await registrar(env.ADHOC_KV, ahora, { resultado: 502, github: gh.status, detalle, pedido });
    return respuesta(502, { ok: false, error: `GitHub respondió ${gh.status}`, detalle });
  }

  await registrar(env.ADHOC_KV, ahora, { resultado: 202, pedido });
  return respuesta(202, {
    ok: true,
    mensaje:
      'Pedido aceptado. El workflow tarda ~1 min; luego export_web lo publica en https://padeldb.es/cola/hoy.json. ' +
      'Si no aparece, el motivo está en el log del workflow.',
    ejecuciones: `https://github.com/${REPO}/actions/workflows/${WORKFLOW}`,
    pedidos_esta_hora: usadas + 1,
  });
}

export async function atenderGet(request, env) {
  if (!env.ADHOC_KEY || !env.ADHOC_KV) {
    return respuesta(503, { ok: false, error: 'Endpoint sin configurar' });
  }
  if (!(await claveValida(request.headers.get('x-adhoc-key'), env.ADHOC_KEY))) {
    return respuesta(401, { ok: false, error: 'X-Adhoc-Key no válida' });
  }
  const lista = await env.ADHOC_KV.list({ prefix: 'log:', limit: 50 });
  const ultimas = lista.keys.map((k) => k.name);
  const entradas = await Promise.all(ultimas.map(async (k) => JSON.parse(await env.ADHOC_KV.get(k))));
  return respuesta(200, { ok: true, llamadas: entradas });
}

export const onRequestPost = ({ request, env }) => atenderPost(request, env);
export const onRequestGet = ({ request, env }) => atenderGet(request, env);
