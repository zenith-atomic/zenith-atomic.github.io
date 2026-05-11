/**
 * Pursuit Scheduler — auto-runs pursuits based on their frequency config.
 * Reads pursuit_index.json to find due pursuits and executes them.
 */
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import cron from 'node-cron';
import yaml from 'js-yaml';
import { runPursuit } from './runner.js';
import { emitter } from '../orchestrator/events.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const INDEX_FILE = join(__dir, 'pursuit_index.json');
const PURSUITS_DIR = join(__dir, 'pursuits');
const FINDINGS_DIR = join(__dir, 'findings');

/** Start the scheduler. Checks for due pursuits every hour. */
export function startScheduler() {
  // Every hour: check for due pursuits
  cron.schedule('0 * * * *', () => runDuePursuits().catch(console.error));
  console.error('[research] Scheduler started — checking pursuits hourly');
}

/** Run all pursuits that are currently due. */
export async function runDuePursuits() {
  const index = loadIndex();
  const now = Date.now();
  const due = index.pursuits.filter(p => p.status === 'active' && isDue(p, now));

  if (due.length === 0) return;

  console.error(`[research] Running ${due.length} due pursuit(s)`);

  for (const p of due) {
    try {
      const result = await runPursuit(p.id);
      updateIndexEntry(p.id, {
        lastRun: new Date().toISOString(),
        latestFinding: result.file,
        status: 'active',
      });

      if (p.notify !== false) {
        emitter.emit('pursuit:notify', {
          id: p.id,
          name: p.name,
          summary: result.summary?.slice(0, 300),
        });
      }
    } catch (err) {
      console.error(`[research] Pursuit ${p.id} failed: ${err.message}`);
      updateIndexEntry(p.id, { lastError: err.message, lastRun: new Date().toISOString() });
    }
  }
}

/** Load or initialize the index. */
export function loadIndex() {
  if (existsSync(INDEX_FILE)) {
    return JSON.parse(readFileSync(INDEX_FILE, 'utf8'));
  }
  return syncIndexFromDisk();
}

/** Rebuild index from pursuits/*.yml files. */
export function syncIndexFromDisk() {
  if (!existsSync(PURSUITS_DIR)) return { pursuits: [] };

  const pursuits = readdirSync(PURSUITS_DIR)
    .filter(f => f.endsWith('.yml'))
    .map(f => {
      const id = f.replace('.yml', '');
      try {
        const cfg = yaml.load(readFileSync(join(PURSUITS_DIR, f), 'utf8'));
        const latestFile = join(FINDINGS_DIR, id, 'latest.md');
        return {
          id,
          name: cfg.name,
          frequency: cfg.frequency || 'weekly',
          status: cfg.status || 'active',
          notify: cfg.notify !== false,
          lastRun: null,
          latestFinding: existsSync(latestFile) ? latestFile : null,
        };
      } catch { return null; }
    })
    .filter(Boolean);

  const index = { pursuits, updated: new Date().toISOString() };
  writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2));
  return index;
}

function updateIndexEntry(id, patch) {
  const index = loadIndex();
  const entry = index.pursuits.find(p => p.id === id);
  if (entry) Object.assign(entry, patch);
  index.updated = new Date().toISOString();
  writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2));
}

const FREQ_MS = {
  hourly: 60 * 60 * 1000,
  daily: 24 * 60 * 60 * 1000,
  weekly: 7 * 24 * 60 * 60 * 1000,
};

function isDue(pursuit, now) {
  if (!pursuit.lastRun) return true;
  const interval = FREQ_MS[pursuit.frequency] || FREQ_MS.daily;
  return now - new Date(pursuit.lastRun).getTime() >= interval;
}
