const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 2 || args[0] !== '--port' || !/^\d+$/.test(args[1])) throw new Error('Explicit opt-in required: node web/tests/ui-01-harness/serve.cjs --port 3015');
  const port = Number(args[1]);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) throw new Error('Use an explicit unprivileged test port.');
  const host = '127.0.0.1';
  assert.equal(host, '127.0.0.1', 'Harness must bind only to loopback.');
  const outputRoot = path.resolve(__dirname, '../../../output/ui-01-harness');
  for (const file of ['index.html', 'harness.js', 'harness.css']) await fs.access(path.join(outputRoot, file));
  const assets = new Map([['/', ['index.html', 'text/html; charset=utf-8']], ['/index.html', ['index.html', 'text/html; charset=utf-8']], ['/harness.js', ['harness.js', 'text/javascript; charset=utf-8']], ['/harness.css', ['harness.css', 'text/css; charset=utf-8']]]);
  const server = http.createServer(async (request, response) => {
    const allowedHost = request.headers.host === `${host}:${port}` || request.headers.host === `localhost:${port}`;
    const remote = request.socket.remoteAddress;
    if (!allowedHost || (remote !== '127.0.0.1' && remote !== '::ffff:127.0.0.1')) { response.writeHead(403); response.end('Loopback test harness only.'); return; }
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    response.setHeader('X-Frame-Options', 'DENY');
    response.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'none'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
    const asset = assets.get(request.url);
    if (!asset || (request.method !== 'GET' && request.method !== 'HEAD')) {
      response.writeHead(503, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ code: 'TEST_HARNESS_SERVICE_UNAVAILABLE', synthetic: true }));
      return;
    }
    try {
      const bytes = await fs.readFile(path.join(outputRoot, asset[0]));
      response.writeHead(200, { 'Content-Type': asset[1] });
      response.end(request.method === 'HEAD' ? undefined : bytes);
    } catch { response.writeHead(503); response.end('Test asset unavailable.'); }
  });
  server.on('error', error => { console.error(error.message); process.exitCode = 1; });
  server.listen(port, host, () => console.log(JSON.stringify({ status: 'TEST HARNESS / SYNTHETIC ONLY', url: `http://${host}:${port}`, outputRoot, backend: 'NONE; assets only; all other paths 503' })));
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
