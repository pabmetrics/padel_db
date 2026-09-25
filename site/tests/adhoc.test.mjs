// node --test tests/  (desde site/) — la Pages Function de /api/adhoc con
// KV y GitHub de mentira.
import assert from 'node:assert/strict';
import test from 'node:test';

import { atenderGet, atenderPost, claveValida, validarPedido } from '../worker/adhoc.js';

class KVFalso {
  constructor() { this.datos = new Map(); }
  async get(k) { return this.datos.get(k) ?? null; }
  async put(k, v) { this.datos.set(k, v); }
  async list({ prefix, limit = 1000 }) {
    const keys = [...this.datos.keys()].filter((k) => k.startsWith(prefix)).sort().slice(0, limit);
    return { keys: keys.map((name) => ({ name })) };
  }
}

const PEDIDO = JSON.stringify({ tipo: 'perfil_top100', sexo: 'F', dimension: 'altura_cm' });

function entorno() {
  return { ADHOC_KEY: 'clave-buena', GITHUB_TOKEN: 'ghp_x', ADHOC_KV: new KVFalso() };
}

function peticion(cuerpo, clave = 'clave-buena', metodo = 'POST') {
  const headers = clave ? { 'x-adhoc-key': clave } : {};
  return new Request('https://padeldb.es/api/adhoc', { method: metodo, headers, body: metodo === 'POST' ? cuerpo : undefined });
}

function githubFalso(estado = 204) {
  const llamadas = [];
  const fetchFn = async (url, opts) => {
    llamadas.push({ url, opts });
    return new Response(estado === 204 ? null : 'mal', { status: estado });
  };
  return { fetchFn, llamadas };
}

const logs = (env) => [...env.ADHOC_KV.datos.keys()].filter((k) => k.startsWith('log:'));

test('claveValida', async () => {
  assert.equal(await claveValida('a', 'a'), true);
  assert.equal(await claveValida('a', 'b'), false);
  assert.equal(await claveValida(null, 'b'), false);
});

test('validarPedido', () => {
  assert.ok(validarPedido(PEDIDO).pedido);
  assert.match(validarPedido('{no').error, /JSON/);
  assert.match(validarPedido('[1]').error, /objeto/);
  assert.match(validarPedido('{"tipo":"otro"}').error, /tipo/);
  assert.match(validarPedido(JSON.stringify({ tipo: 'jugadores', x: 'a'.repeat(5000) })).error, /bytes/);
});

test('sin configurar -> 503', async () => {
  assert.equal((await atenderPost(peticion(PEDIDO), {})).status, 503);
});

test('clave mala -> 401, sin llamar a GitHub ni escribir en KV', async () => {
  const env = entorno();
  const { fetchFn, llamadas } = githubFalso();
  assert.equal((await atenderPost(peticion(PEDIDO, 'otra'), env, { fetchFn })).status, 401);
  assert.equal((await atenderPost(peticion(PEDIDO, null), env, { fetchFn })).status, 401);
  assert.equal(llamadas.length, 0);
  assert.equal(env.ADHOC_KV.datos.size, 0);
});

test('JSON inválido -> 400, registrado, sin llamar a GitHub', async () => {
  const env = entorno();
  const { fetchFn, llamadas } = githubFalso();
  assert.equal((await atenderPost(peticion('{mal'), env, { fetchFn })).status, 400);
  assert.equal(llamadas.length, 0);
  assert.equal(logs(env).length, 1);
});

test('pedido válido -> 202 y dispatch en main con el pedido como input', async () => {
  const env = entorno();
  const { fetchFn, llamadas } = githubFalso();
  const r = await atenderPost(peticion(PEDIDO), env, { fetchFn });
  assert.equal(r.status, 202);
  assert.equal(llamadas.length, 1);
  assert.match(llamadas[0].url, /repos\/pabmetrics\/padel_db\/actions\/workflows\/adhoc_chart\.yml\/dispatches$/);
  assert.equal(llamadas[0].opts.headers.authorization, 'Bearer ghp_x');
  const body = JSON.parse(llamadas[0].opts.body);
  assert.equal(body.ref, 'main');
  assert.deepEqual(JSON.parse(body.inputs.pedido), JSON.parse(PEDIDO));
  assert.ok(!JSON.stringify(await r.json()).includes('ghp_x'), 'el token nunca vuelve en la respuesta');
});

test('GitHub falla -> 502 con su estado', async () => {
  const env = entorno();
  const { fetchFn } = githubFalso(403);
  const r = await atenderPost(peticion(PEDIDO), env, { fetchFn });
  assert.equal(r.status, 502);
  assert.match((await r.json()).error, /403/);
});

test('20 por hora -> 429; la hora siguiente vuelve a aceptar', async () => {
  const env = entorno();
  const { fetchFn, llamadas } = githubFalso();
  const ahora = new Date('2026-09-25T16:10:00Z');
  for (let i = 0; i < 20; i++) {
    assert.equal((await atenderPost(peticion(PEDIDO), env, { fetchFn, ahora })).status, 202);
  }
  assert.equal((await atenderPost(peticion(PEDIDO), env, { fetchFn, ahora })).status, 429);
  assert.equal(llamadas.length, 20);
  const luego = new Date('2026-09-25T17:00:00Z');
  assert.equal((await atenderPost(peticion(PEDIDO), env, { fetchFn, ahora: luego })).status, 202);
});

test('GET devuelve el log, lo más reciente primero', async () => {
  const env = entorno();
  const { fetchFn } = githubFalso();
  await atenderPost(peticion(PEDIDO), env, { fetchFn, ahora: new Date('2026-09-25T10:00:00Z') });
  await atenderPost(peticion('{mal'), env, { fetchFn, ahora: new Date('2026-09-25T11:00:00Z') });
  assert.equal((await atenderGet(peticion(null, 'otra', 'GET'), env)).status, 401);
  const { llamadas } = await (await atenderGet(peticion(null, 'clave-buena', 'GET'), env)).json();
  assert.deepEqual(llamadas.map((l) => l.resultado), [400, 202]);
});
