// Lectura de los ficheros que escribe `transform/export_web.py` en public/datos
// (solo filas publicables). Corre en el build de Astro, desde `site/`.
import fs from 'node:fs';
import path from 'node:path';

const DIR = path.join(process.cwd(), 'public', 'datos');

export function leer(tabla) {
  return JSON.parse(fs.readFileSync(path.join(DIR, `${tabla}.json`), 'utf8'));
}

export function catalogo() {
  return JSON.parse(fs.readFileSync(path.join(DIR, 'catalogo.json'), 'utf8'));
}

export function fechaDe(tabla) {
  return catalogo().find((t) => t.tabla === tabla)?.fecha_dato ?? null;
}

export function existeImagen(nombre) {
  return fs.existsSync(path.join(process.cwd(), 'public', 'img', nombre));
}

// Formato numérico español siempre: punto de miles (también en 4 cifras) y coma decimal.
export function num(n, decimales = 0) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('de-DE', { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

export function delta(n, decimales = 0) {
  if (n === null || n === undefined) return '—';
  const r = Number(n.toFixed(decimales)); // un +0,0 % no lleva signo
  return `${r > 0 ? '+' : r < 0 ? '−' : ''}${num(Math.abs(r), decimales)}`;
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
export function fechaLarga(iso) {
  if (!iso) return '';
  const [a, m, d] = iso.split('-').map(Number);
  return `${d} de ${MESES[m - 1]} de ${a}`;
}

export function porSexo(filas, campo = 'sexo') {
  return { M: filas.filter((f) => f[campo] === 'M'), F: filas.filter((f) => f[campo] === 'F') };
}

export function porCategoria(filas) {
  return { men: filas.filter((f) => f.categoria === 'men'), women: filas.filter((f) => f.categoria === 'women') };
}
