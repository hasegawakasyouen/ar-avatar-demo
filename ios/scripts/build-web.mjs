import { copyFile, mkdir } from 'node:fs/promises';
import { build } from 'esbuild';

await mkdir('Web/dist', { recursive: true });
await build({
  entryPoints: ['Web/src/main.js'],
  bundle: true,
  minify: true,
  outfile: 'Web/dist/mascot.js',
});
await copyFile('Web/src/index.html', 'Web/dist/index.html');
