import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/demo.mjs', ['demo.mjs', 'text/javascript; charset=utf-8']],
  ['/state.mjs', ['state.mjs', 'text/javascript; charset=utf-8']],
]);
const port = Number(process.env.FORMS_DEMO_PORT || 4173);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid FORMS_DEMO_PORT.');
createServer(async (request, response) => {
  const file = request.method === 'GET' ? files.get(request.url) : null;
  if (!file) { response.writeHead(404); response.end('Not found'); return; }
  try {
    const bytes = await readFile(fileURLToPath(new URL(file[0], import.meta.url)));
    response.writeHead(200, { 'Content-Type': file[1], 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' });
    response.end(bytes);
  } catch { response.writeHead(500); response.end('Unable to load demo'); }
}).listen(port, '127.0.0.1', () => console.log(`Synthetic forms demo: http://127.0.0.1:${port}`));
