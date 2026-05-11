import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, renameSync } from 'fs';
import { join } from 'path';

const FACTORY = process.env.FACTORY_DIR || join(process.env.HOME, '.openclaw/workspace/factory');
const RUNS_DIR = join(FACTORY, 'output', 'runs');

export function createRun(brief) {
  mkdirSync(RUNS_DIR, { recursive: true });
  const runId = `run_${Date.now()}`;
  const state = {
    id: runId,
    brief: brief.slice(0, 500),
    created: new Date().toISOString(),
    updated: new Date().toISOString(),
    phase: 'init',
    atoms: null,
    studioResults: {},
    queuedIds: [],
    error: null,
  };
  _write(runId, state);
  return runId;
}

export function updateRun(runId, patch) {
  const state = getState(runId);
  const updated = { ...state, ...patch, updated: new Date().toISOString() };
  _write(runId, updated);
  return updated;
}

export function getState(runId) {
  const file = join(RUNS_DIR, `${runId}.json`);
  if (!existsSync(file)) throw new Error(`Run not found: ${runId}`);
  return JSON.parse(readFileSync(file, 'utf8'));
}

export function listRuns(limit = 20) {
  if (!existsSync(RUNS_DIR)) return [];
  return readdirSync(RUNS_DIR)
    .filter(f => f.endsWith('.json'))
    .sort().reverse()
    .slice(0, limit)
    .map(f => JSON.parse(readFileSync(join(RUNS_DIR, f), 'utf8')));
}

function _write(runId, data) {
  const file = join(RUNS_DIR, `${runId}.json`);
  const tmp = file + '.tmp';
  writeFileSync(tmp, JSON.stringify(data, null, 2));
  renameSync(tmp, file);
}
