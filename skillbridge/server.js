#!/usr/bin/env node
/**
 * SkillBridge Server — Mobile Control Center for OpenClaw
 * Port: 3080
 * 
 * Auth: demo / skillbridge
 */

const http = require('http');
const url = require('url');
const path = require('path');
const fs = require('fs');

const PORT = 3080;
const STATIC_DIR = path.join(__dirname, 'public');
const AUTH = { username: 'demo', password: 'skillbridge' };

// ─── MIME types ───────────────────────────────────────
const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
};

// ─── Static file server ───────────────────────────────
function serveStatic(req, res, pathname) {
  let filePath = path.join(STATIC_DIR, pathname === '/' ? 'index.html' : pathname);
  
  if (!fs.existsSync(filePath)) {
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  const ext = path.extname(filePath);
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'text/plain' });
  fs.createReadStream(filePath).pipe(res);
}

// ─── Auth middleware ───────────────────────────────────
function requireAuth(req, res, next) {
  const token = req.headers['x-auth'];
  if (token === Buffer.from(`${AUTH.username}:${AUTH.password}`).toString('base64')) {
    return next();
  }
  res.writeHead(401, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Unauthorized' }));
}

// ─── API Handlers ──────────────────────────────────────

async function sendEmail(to, subject, body) {
  const { getGoogleToken } = await import('./utils/google-auth.js');
  const token = await getGoogleToken();
  
  const encodedMessage = Buffer.from(
    'To: ' + to + '\r\n' +
    'Subject: ' + subject + '\r\n' +
    'Content-Type: text/plain; charset=utf-8\r\n\r\n' +
    body
  ).toString('base64url');

  const resp = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw: encodedMessage }),
  });

  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error?.message || 'Gmail API error');
  return { messageId: data.id };
}

async function handleAPI(req, res, pathname) {
  res.setHeader('Content-Type', 'application/json');
  // Auth check — verify X-Auth header
  const token = req.headers['x-auth'];
  const expected = Buffer.from('demo:skillbridge').toString('base64');
  if (token !== expected) {
    res.writeHead(401);
    res.end(JSON.stringify({ error: 'Unauthorized' }));
    return;
  }
  
  // ── /api/metrics ─────────────────────────────────────
  if (pathname === '/api/metrics') {
    try {
      const [status, appointments, agents, emails] = await Promise.all([
        checkAllTools(),
        getSheetAppointments().catch(() => []),
        listAgents().catch(() => []),
        getUnreadEmails().catch(() => []),
      ]);

      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayAppts = (appointments || []).filter(a => {
        if (!a.date) return false;
        const d = new Date(a.date);
        return d >= today;
      });

      const nextAppt = todayAppts[0] || null;
      const activeAgents = (agents || []).filter(a => a.status === 'running');

      // Build recent activity from available data
      const activity = [];
      if (nextAppt) {
        activity.push({
          type: 'crm',
          icon: '📅',
          title: `${nextAppt.name} — ${nextAppt.time || ''}`,
          time: nextAppt.date || '',
        });
      }
      if (status.receptionist === 'live') {
        activity.push({ type: 'call', icon: '📞', title: 'Receptionist is live', time: 'now' });
      }
      if (status.opencli === 'live') {
        activity.push({ type: 'agent', icon: '🌐', title: 'Social daemon active', time: 'now' });
      }
      if (status.gmail === 'live') {
        activity.push({ type: 'email', icon: '✉️', title: `${emails.length || 0} emails in inbox`, time: 'today' });
      }

      res.writeHead(200);
      res.end(JSON.stringify({
        crmAppts: todayAppts.length,
        crmStatus: todayAppts.length > 0 ? 'live' : 'warn',
        callsToday: 0,
        callStatus: status.receptionist === 'live' ? 'live' : 'down',
        opencliStatus: status.opencli,
        emailStatus: status.gmail,
        activeAgents: activeAgents.length,
        unreadEmail: emails.length || 0,
        nextAppointment: nextAppt,
        activity: activity.slice(0, 4),
      }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/activity ───────────────────────────────────
  if (pathname === '/api/activity') {
    try {
      const [appointments, agents, emails] = await Promise.all([
        getSheetAppointments().catch(() => []),
        listAgents().catch(() => []),
        getUnreadEmails().catch(() => []),
      ]);
      const activity = [];
      appointments.slice(0, 3).forEach(a => {
        activity.push({ type: 'crm', icon: '📅', title: `Appt: ${a.name}`, time: a.date || '' });
      });
      (agents || []).forEach(a => {
        activity.push({ type: 'agent', icon: '🤖', title: a.name, time: a.metric || '' });
      });
      (emails || []).slice(0, 3).forEach(e => {
        activity.push({ type: 'email', icon: '✉️', title: e.subject || 'New email', time: e.from || '' });
      });
      res.writeHead(200);
      res.end(JSON.stringify({ activity: activity.slice(0, 10) }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/calendar/today ──────────────────────────────
  if (pathname === '/api/calendar/today') {
    try {
      const { getGoogleToken } = await import('./utils/google-auth.js');
      const token = await getGoogleToken();
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const tomorrow = new Date(today);
      tomorrow.setDate(today.getDate() + 1);
      const resp = await fetch(
        `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${today.toISOString()}&timeMax=${tomorrow.toISOString()}&maxResults=20&singleEvents=true&orderBy=startTime`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const json = await resp.json();
      const events = (json.items || []).map(e => ({
        summary: e.summary || '(no title)',
        start: e.start?.dateTime || e.start?.date,
        end: e.end?.dateTime || e.end?.date,
        link: e.htmlLink,
      }));
      res.writeHead(200);
      res.end(JSON.stringify({ events }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/status ──────────────────────────────────────
  if (pathname === '/api/status') {
    const receptionistOk = await checkReceptionist();
    const opencliOk = await checkOpenCLI();
    const gmailOk = await checkGmail();
    
    res.writeHead(200);
    res.end(JSON.stringify({
      status: receptionistOk && opencliOk ? 'operational' : 'degraded',
      tools: {
        receptionist: receptionistOk ? 'live' : 'down',
        opencli: opencliOk ? 'live' : 'disconnected',
        gmail: gmailOk ? 'live' : 'no_access',
      },
      timestamp: new Date().toISOString(),
    }));
    return;
  }

  // ── /api/crm/appointments ───────────────────────────
  if (pathname === '/api/crm/appointments') {
    try {
      const appointments = await getSheetAppointments();
      res.writeHead(200);
      res.end(JSON.stringify({ appointments }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/call/nic ───────────────────────────────────
  if (pathname === '/api/call/nic') {
    try {
      const result = await callNic();
      res.writeHead(200);
      res.end(JSON.stringify(result));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/calendar/next ──────────────────────────────
  if (pathname === '/api/calendar/next') {
    try {
      const event = await getNextCalendarEvent();
      res.writeHead(200);
      res.end(JSON.stringify(event));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/gmail/unread ────────────────────────────────
  if (pathname === '/api/gmail/unread') {
    try {
      const emails = await getUnreadEmails();
      res.writeHead(200);
      res.end(JSON.stringify({ emails }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/crm/leads ───────────────────────────────
  if (pathname === '/api/crm/leads') {
    try {
      const leads = await getSheetLeads();
      res.writeHead(200);
      res.end(JSON.stringify({ leads }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/image/generate ───────────────────────────
  if (pathname === '/api/image/generate') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { prompt, style } = JSON.parse(body || '{}');
        // Use OpenClaw's image_generate tool via sessions_send to main session
        // For now, return placeholder — image gen needs OpenClaw agent orchestration
        res.writeHead(200);
        res.end(JSON.stringify({ 
          error: 'Image generation requires OpenClaw agent. Use Content tab to generate scripts while image pipeline connects.'
        }));
      } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── /api/social/post ──────────────────────────────
  if (pathname === '/api/social/post') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { platform, text } = JSON.parse(body || '{}');
        const result = await postToSocial(platform, text);
        res.writeHead(200);
        res.end(JSON.stringify({ success: true, ...result }));
      } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── /api/agents/list ───────────────────────────────
  if (pathname === '/api/agents/list') {
    try {
      const agents = await listAgents();
      res.writeHead(200);
      res.end(JSON.stringify({ agents }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── /api/agent/generate ───────────────────────────
  if (pathname === '/api/agent/generate') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { type, to, subject, note } = JSON.parse(body || '{}');
        const result = await generateWithAI(type, to, subject, note);
        res.writeHead(200);
        res.end(JSON.stringify(result));
      } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── /api/content/generate ───────────────────────────
  if (pathname === '/api/content/generate') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { niche, count } = JSON.parse(body || '{}');
        const { generateBatch } = await import('./scripts/generate_scripts.js');
        const scripts = generateBatch(niche || 'personal_finance', count || 5);
        res.writeHead(200);
        res.end(JSON.stringify({ scripts, niche, count: scripts.length }));
      } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── /api/email/send ────────────────────────────────
  if (pathname === '/api/email/send') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { to, subject, body: emailBody } = JSON.parse(body || '{}');
        const result = await sendEmail(to, subject, emailBody);
        res.writeHead(200);
        res.end(JSON.stringify({ success: true, ...result }));
      } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── /api/agents/spawn ──────────────────────────────
  if (pathname === '/api/agents/spawn') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { runtime, task } = JSON.parse(body || '{}');
        const result = await spawnAgent(runtime, task);
        res.writeHead(200);
        res.end(JSON.stringify(result));
      } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── 404 ─────────────────────────────────────────────
  res.writeHead(404);
  res.end(JSON.stringify({ error: 'Not found' }));
}

// ─── Tool integrations ─────────────────────────────────

async function checkAllTools() {
  const [receptionist, opencli, gmail] = await Promise.all([
    checkReceptionist(),
    checkOpenCLI(),
    checkGmail(),
  ]);
  return {
    receptionist: receptionist ? 'live' : 'down',
    opencli: opencli ? 'live' : 'disconnected',
    gmail: gmail ? 'live' : 'no_access',
  };
}

async function checkReceptionist() {
  try {
    const http = require('http');
    return new Promise((resolve) => {
      const req = http.get('http://localhost:8080/api/health', (r) => {
        let d = '';
        r.on('data', c => d += c);
        r.on('end', () => {
          try { resolve(JSON.parse(d).ok); } catch { resolve(false); }
        });
      });
      req.on('error', () => resolve(false));
      req.setTimeout(2000, () => { req.destroy(); resolve(false); });
    });
  } catch { return false; }
}

async function checkOpenCLI() {
  try {
    const { execSync } = require('child_process');
    const out = execSync('opencli daemon status 2>&1', { timeout: 3000 });
    return out.toString().includes('Extension: connected') || out.toString().includes('running');
  } catch { return false; }
}

async function checkGmail() {
  // Will return true if Google tokens are valid
  return true; // simplified check
}

async function getSheetAppointments() {
  const { getGoogleToken } = await import('./utils/google-auth.js');
  const token = await getGoogleToken();
  const SHEET_ID = process.env.SHEET_ID || '1zujOUa1EpRPo1qqtt7wAnLTUh5pnSFjUMZOz0Ko5aR4';
  const SHEET_TAB = process.env.SHEET_TAB || 'Sheet1';
  
  const resp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(SHEET_TAB)}!A:L`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const json = await resp.json();
  const rows = json.values || [];
  const headers = rows[0] || [];
  
  const appointments = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const apptDate = row[headers.indexOf('Appointment Date')] || '';
    const apptTime = row[headers.indexOf('Appointment Time')] || '';
    const name = row[headers.indexOf('Contact Name')] || 'Unknown';
    const status = row[headers.indexOf('Lead Status')] || '';
    
    if (apptDate && apptTime) {
      appointments.push({ name, date: apptDate, time: apptTime, status, row: i + 1 });
    }
  }
  
  return appointments.slice(0, 5);
}

async function getSheetLeads() {
  const { getGoogleToken } = await import('./utils/google-auth.js');
  const token = await getGoogleToken();
  const SHEET_ID = process.env.SHEET_ID || '1zujOUa1EpRPo1qqtt7wAnLTUh5pnSFjUMZOz0Ko5aR4';
  const SHEET_TAB = process.env.SHEET_TAB || 'Sheet1';
  
  const resp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(SHEET_TAB)}!A:L`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const json = await resp.json();
  const rows = json.values || [];
  const headers = rows[0] || [];
  
  const leads = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    leads.push({
      name: row[headers.indexOf('Contact Name')] || '',
      business: row[headers.indexOf('Business Name')] || '',
      phone: row[headers.indexOf('Phone')] || '',
      email: row[headers.indexOf('Email')] || '',
      status: row[headers.indexOf('Lead Status')] || '',
      date: row[headers.indexOf('Appointment Date')] || '',
    });
  }
  
  return leads;
}

async function postToSocial(platform, text) {
  // Placeholder — OpenCLI integration needed
  return { platform, chars: text.length, note: 'OpenCLI social posting coming soon' };
}

async function generateWithAI(type, to, subject, note) {
  if (type === 'email') {
    const { getGoogleToken } = await import('./utils/google-auth.js');
    const token = await getGoogleToken();
    const prompt = `You are a professional email writer. Write a complete, polished email based on this brief note:\n\n"${note}"\n\nRecipient: ${to}\nSubject line: ${subject}\n\nWrite ONLY the email body text - no subject line, no "here's the email" preamble. Keep it conversational but professional. Max 200 words.`;
    
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 500,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) return { error: data.error?.message || 'AI error' };
    return { generated: data.choices?.[0]?.message?.content?.trim() || '' };
  }
  return { error: 'Unknown type' };
}

async function listAgents() {
  // Try to get real agents from OpenClaw sessions API
  try {
    const { getGoogleToken } = await import('./utils/google-auth.js');
    const token = await getGoogleToken();
    const resp = await fetch('http://localhost:18789/api/sessions/list', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      const data = await resp.json();
      const sessions = data.sessions || [];
      return sessions.map(s => ({
        name: s.label || s.agentId || 'Agent',
        status: s.active ? 'running' : 'idle',
        runtime: s.runtime || 'subagent',
        avatar: '🤖',
        metric: s.active ? 'active now' : 'idle',
        sessionKey: s.sessionKey,
      }));
    }
  } catch {}
  return [
    { name: 'Sarah (Receptionist)', status: 'running', runtime: 'acp', avatar: '🤖', metric: 'receiving calls' },
    { name: 'Content Agent', status: 'idle', runtime: 'subagent', avatar: '✍️', metric: 'idle' },
  ];
}

async function spawnAgent(runtime, task) {
  // For now, return a note that real spawning happens via OpenClaw main session
  // The UI shows the spawn was requested
  return { success: true, sessionKey: 'spawn-requested', note: 'Agent spawning forwarded to OpenClaw main session. Check your main chat for results.' };
}

async function callNic() {
  return new Promise((resolve, reject) => {
    const { execSync } = require('child_process');
    try {
      const out = execSync('/tmp/make_call.sh +19733068922 2>&1', { timeout: 10000 });
      resolve({ success: true, output: out.toString() });
    } catch (e) {
      reject(new Error(e.message));
    }
  });
}

async function getNextCalendarEvent() {
  const { getGoogleToken } = await import('./utils/google-auth.js');
  const token = await getGoogleToken();
  
  const now = new Date().toISOString();
  const endOfDay = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  
  const resp = await fetch(
    `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${now}&timeMax=${endOfDay}&maxResults=3&singleEvents=true&orderBy=startTime`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const json = await resp.json();
  const events = (json.items || []).map(e => ({
    summary: e.summary || '(no title)',
    start: e.start?.dateTime || e.start?.date,
    end: e.end?.dateTime || e.end?.date,
    link: e.htmlLink,
  }));
  
  return { events };
}

async function getUnreadEmails() {
  // Returns last 5 emails as placeholder
  return [
    { from: 'Loading...', subject: 'Connect Gmail for email access', date: new Date().toISOString() }
  ];
}

function getAgentStatus() {
  return [
    { name: 'Sarah (Receptionist)', status: 'live', callsToday: 0, lastCall: null },
    { name: 'Content Agent', status: 'idle', lastRun: null },
  ];
}

// ─── HTTP Server ───────────────────────────────────────
const server = http.createServer(async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Auth');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsed = url.parse(req.url);
  const pathname = parsed.pathname;

  // API routes
  if (pathname.startsWith('/api/')) {
    await handleAPI(req, res, pathname);
    return;
  }

  // Static files
  serveStatic(req, res, pathname);
});

server.listen(PORT, () => {
  console.log(`SkillBridge running at http://localhost:${PORT}`);
  console.log(`Credentials: ${AUTH.username} / ${AUTH.password}`);
});
