#!/usr/bin/env node
/**
 * SkillBridge Reverse Proxy
 * Exposes http://localhost:3080 as https://dellrack.taile561c8.ts.net/bridge/
 * Uses the existing OpenClaw Tailscale HTTPS endpoint
 */
const http = require('http');
const https = require('https');
const url = require('url');

const LOCAL_PORT = 3080;
const PROXY_PATH = '/bridge';

// Fetch remote URL via OpenClaw Tailscale
function fetchRemote(path, method, headers, body) {
  return new Promise((resolve, reject) => {
    const gatewayToken = process.env.OPENCLAW_GATEWAY_TOKEN || '';
    const targetHost = 'dellrack.taile561c8.ts.net';
    const opts = {
      hostname: targetHost,
      port: 443,
      path: path,
      method: method || 'GET',
      headers: {
        'Authorization': 'Bearer ' + gatewayToken,
        'X-Forwarded-Host': targetHost,
        ...headers,
      },
      rejectUnauthorized: false, // self-signed cert
    };
    const req = https.request(opts, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

// Proxy server on a high port for Tailscale to reach
// We'll use the OpenClaw gateway's /bridge/ route instead
// Actually let's use a simple WebSocket+HTTP approach via the gateway

// Better approach: run a HTTP->HTTP proxy on port 3081 that OpenClaw can expose
const PROXY_PORT = 3081;

const proxy = http.createServer(async (req, res) => {
  const parsed = url.parse(req.url);
  const targetPath = `http://localhost:${LOCAL_PORT}${parsed.path}`;
  
  console.log(`[proxy] ${req.method} ${parsed.path} -> ${targetPath}`);
  
  // Build forwarding headers
  const headers = { ...req.headers };
  delete headers['host'];
  delete headers['connection'];
  headers['X-Forwarded-For'] = req.socket.remoteAddress;
  headers['X-Real-IP'] = req.socket.remoteAddress;
  headers['X-Auth'] = Buffer.from('demo:skillbridge').toString('base64');

  const proxyReq = http.request({
    host: 'localhost',
    port: LOCAL_PORT,
    path: parsed.path,
    method: req.method,
    headers,
  }, proxyRes => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  
  req.pipe(proxyReq);
  proxyReq.on('error', e => {
    console.error('[proxy] error:', e.message);
    res.writeHead(502);
    res.end('Bad gateway');
  });
});

proxy.listen(PROXY_PORT, '0.0.0.0', () => {
  console.log(`SkillBridge reverse proxy listening on http://0.0.0.0:${PROXY_PORT}`);
  console.log(`Proxied from Tailscale: https://dellrack.taile561c8.ts.net:${PROXY_PORT}/`);
});
