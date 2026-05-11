#!/usr/bin/env node
/**
 * steel-cdp-proxy — adapts Steel Browser's /v1/sessions API to standard Chrome CDP HTTP endpoints.
 *
 * Steel Browser proxies Chrome CDP over WebSocket on port 3000 but does not expose the
 * standard HTTP CDP endpoints (/json/list, /json/version) that openclaw expects.
 *
 * This proxy:
 *   - Listens on PROXY_PORT (default 9222)
 *   - GET /json/list  -> queries Steel /v1/sessions and maps to CDP target format
 *   - GET /json       -> same as /json/list
 *   - GET /json/version -> Chrome version stub
 *   - WebSocket       -> proxied to Steel ws://127.0.0.1:STEEL_PORT/
 */

'use strict';

const http = require('http');
const net = require('net');

const STEEL_HOST = '127.0.0.1';
const STEEL_PORT = parseInt(process.env.STEEL_PORT ?? '3000', 10);
const PROXY_PORT = parseInt(process.env.PROXY_PORT ?? '9222', 10);
const PROXY_HOST = '127.0.0.1';

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`JSON parse error from ${url}: ${e.message} — body: ${data.slice(0, 200)}`)); }
      });
    }).on('error', reject);
  });
}

async function buildTargetList() {
  const result = await fetchJson(`http://${STEEL_HOST}:${STEEL_PORT}/v1/sessions`);
  const sessions = Array.isArray(result) ? result : (result.sessions ?? []);
  return sessions.map((s) => ({
    id: s.id,
    type: 'page',
    title: `Steel Browser Session`,
    url: 'about:blank',
    webSocketDebuggerUrl: `ws://${PROXY_HOST}:${PROXY_PORT}/devtools/page/${s.id}`,
    devtoolsFrontendUrl: `/devtools/inspector.html?ws=${PROXY_HOST}:${PROXY_PORT}/devtools/page/${s.id}`,
    description: '',
    faviconUrl: '',
  }));
}

const VERSION_STUB = {
  Browser: 'Chrome/120.0.0.0',
  'Protocol-Version': '1.3',
  'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
  'V8-Version': '12.0.0',
  'WebKit-Version': '537.36',
  webSocketDebuggerUrl: `ws://${PROXY_HOST}:${PROXY_PORT}/`,
};

const server = http.createServer(async (req, res) => {
  const url = req.url ?? '/';
  if (url === '/json' || url === '/json/list' || url.startsWith('/json/list?')) {
    try {
      const targets = await buildTargetList();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(targets));
    } catch (e) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: String(e) }));
    }
    return;
  }
  if (url === '/json/version') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(VERSION_STUB));
    return;
  }
  if (url === '/json/new' || url.startsWith('/json/new?')) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Steel browser: use /v1/sessions to create sessions' }));
    return;
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not Found' }));
});

// WebSocket upgrade: proxy to Steel WebSocket on port 3000.
// Steel only accepts WebSocket connections at the root path '/'.
// Any per-target path (e.g. /devtools/page/ID) is remapped to '/'.
// Strategy: intercept the upgrade, perform the handshake with Steel ourselves,
// then stitch the two raw sockets together for the CDP frame stream.
server.on('upgrade', (req, clientSocket, head) => {
  clientSocket.on('error', (err) => {
    console.error('[steel-cdp-proxy] client WS error:', err.message);
  });

  const key = req.headers['sec-websocket-key'] ?? '';
  const steelSocket = net.connect(STEEL_PORT, STEEL_HOST, () => {
    const wsReq = [
      'GET / HTTP/1.1',
      `Host: ${STEEL_HOST}:${STEEL_PORT}`,
      'Upgrade: websocket',
      'Connection: Upgrade',
      `Sec-WebSocket-Key: ${key}`,
      'Sec-WebSocket-Version: 13',
      '',
      '',
    ].join('\r\n');
    steelSocket.write(wsReq);
  });

  steelSocket.on('error', (err) => {
    console.error('[steel-cdp-proxy] upstream WS error:', err.message);
    clientSocket.destroy();
  });

  // Buffer all incoming data from Steel until we see the end of the HTTP 101 headers.
  // Then forward the 101 to the client and wire up bidirectional piping.
  let buf = Buffer.alloc(0);
  let handshakeDone = false;

  steelSocket.on('data', (chunk) => {
    if (handshakeDone) return; // pipe handles it after this point
    buf = Buffer.concat([buf, chunk]);
    const sep = buf.indexOf('\r\n\r\n');
    if (sep < 0) return; // still waiting for end of headers

    handshakeDone = true;
    const headerPart = buf.slice(0, sep + 4); // include the final \r\n\r\n
    const remainder = buf.slice(sep + 4);

    // Forward Steel's 101 response to the client
    clientSocket.write(headerPart);
    if (remainder.length > 0) clientSocket.write(remainder);

    // Now stitch the two sockets together for CDP framing
    steelSocket.pipe(clientSocket);
    clientSocket.pipe(steelSocket);

    if (head && head.length > 0) steelSocket.write(head);
  });

  clientSocket.on('close', () => steelSocket.destroy());
  steelSocket.on('close', () => clientSocket.destroy());
});

server.listen(PROXY_PORT, PROXY_HOST, () => {
  console.log(`[steel-cdp-proxy] listening on ${PROXY_HOST}:${PROXY_PORT} → Steel ${STEEL_HOST}:${STEEL_PORT}`);
});

server.on('error', (err) => {
  console.error('[steel-cdp-proxy] server error:', err.message);
  process.exit(1);
});
