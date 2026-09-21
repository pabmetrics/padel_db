// Quita de dist/ lo que todavía no debe estar en línea. export_web sigue
// escribiendo estas carpetas en public/ (el pipeline no cambia); solo se
// excluyen del despliegue. Al publicar cada sección, borra su línea de aquí.
import fs from 'node:fs';
import path from 'node:path';

const NO_PUBLICAR = [
  'datos', // descargas CSV/JSON: salen con la página /datos/
  'cola',  // cola para Cowork: sale cuando se conecte la tarea programada
];

for (const carpeta of NO_PUBLICAR) {
  fs.rmSync(path.join('dist', carpeta), { recursive: true, force: true });
  console.log(`despublicar: dist/${carpeta} excluida del despliegue`);
}
