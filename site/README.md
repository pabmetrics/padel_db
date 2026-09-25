# site — web de PadelDB (Astro)

Sitio estático. Lee los ficheros que deja `transform/export_web.py` en `public/`
(`datos/`, `img/`, `cola/`) y no llama a ninguna API en el build.

```
site/
├── public/          # lo escribe export_web (datos, img, cola, fonts, brand); se commitea
├── src/
│   ├── layouts/Base.astro     # cabecera, navegación, pie, metadatos
│   ├── components/            # Tabla, Figura
│   ├── lib/datos.js           # lectura de public/datos y formato numérico español
│   ├── styles/global.css      # tokens de marca (doc 02 §1.2), claro/oscuro
│   └── pages/                 # ranking, torneos, parejas, jugadores, mapa-de-pistas,
│                              # mercado, datos, metodologia, sobre, guias/*
└── astro.config.mjs
```

## En local

```
python transform/export_web.py     # desde la raíz del repo: refresca site/public
cd site
npm install
npm run dev                        # http://localhost:4321
npm run build                      # genera dist/
```

## Despliegue: Cloudflare Pages

Conectar el repo en Cloudflare Pages (integración con GitHub, sin secretos):

| Ajuste | Valor |
|---|---|
| Directorio raíz | `site` |
| Comando de build | `npm run build` |
| Directorio de salida | `dist` |
| Variable de entorno | `NODE_VERSION` = `22` |

Cada commit de los jobs (`export_web`, `build_silver_gold`, …) que llega a `main`
provoca un nuevo build. Analítica sin cookies: activar Cloudflare Web Analytics
en el panel (no requiere código).

## La cola

`public/cola/hoy.json` (solo la de hoy; `[]` si no hay), `public/cola/<fecha>.json`
y `public/cola/indice.json` (series previstas y recuento) son la cola del día para la
tarea programada de Cowork (doc 03 §6, `docs/cowork-puesta-en-marcha.md`). Se despliegan. No se enlazan desde ningún menú y
`_headers` (`X-Robots-Tag: noindex, nofollow`) las deja fuera de los buscadores. No se
bloquean en `robots.txt`: el fetcher de Cowork lo respeta y devolvería `ROBOTS_DISALLOWED`.

## Qué no hace

- No publica nada en X ni en ninguna red: la web solo muestra datos.
- Solo muestra filas `publicable` de gold.
- No hay formulario de newsletter ni analítica propia todavía.

## Publicación por secciones

Ahora mismo solo está publicada la landing (`src/pages/index.astro`, sin navegación ni enlaces).
El resto de secciones ya están hechas y viven en `src/pendientes/`, que Astro no enruta.

- **Publicar una sección:** `git mv src/pendientes/ranking.astro src/pages/` (las guías van a
  `src/pages/guias/`). Después, en `src/layouts/Base.astro` deja en `enlaces` solo las secciones ya
  publicadas (la lista trae las 8, y un enlace a una sección aún pendiente daría 404). La navegación y el
  pie completos salen en las páginas que no usan `minimo`; la landing sigue con `minimo` hasta que se lo quites.
- **Datos y cola:** `scripts/despublicar.mjs` excluye `datos/` y `cola/` del despliegue.
  Quita cada línea cuando publiques la página de descargas o conectes la tarea de Cowork.
