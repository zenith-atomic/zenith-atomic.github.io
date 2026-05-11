import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, renameSync } from 'fs';
import { join } from 'path';

const FACTORY = process.env.FACTORY_DIR || join(process.env.HOME, '.openclaw/workspace/factory');
const QUEUE_DIR = join(FACTORY, 'queue');

export function addToQueue(studioOutput, runId) {
  const week = currentWeek();
  const weekDir = join(QUEUE_DIR, week);
  mkdirSync(weekDir, { recursive: true });

  const id = `${Date.now()}-${studioOutput.platform}`;
  const entry = {
    id,
    runId,
    week,
    platform: studioOutput.platform,
    contentType: studioOutput.contentType,
    content: studioOutput.content,
    metadata: studioOutput.metadata || {},
    created: new Date().toISOString(),
    status: 'pending',
    scheduled_time: null,
  };

  writeFileSync(join(weekDir, `${id}.json`), JSON.stringify(entry, null, 2));
  _syncApproval(week, weekDir);
  return id;
}

export function approve(postId) { return _setStatus(postId, 'approved'); }
export function skip(postId) { return _setStatus(postId, 'skipped'); }

export function getQueue(week = currentWeek()) {
  const weekDir = join(QUEUE_DIR, week);
  if (!existsSync(weekDir)) return [];
  return readdirSync(weekDir)
    .filter(f => f.endsWith('.json') && f !== 'approval.json')
    .map(f => JSON.parse(readFileSync(join(weekDir, f), 'utf8')));
}

export function getApproval(week = currentWeek()) {
  const file = join(QUEUE_DIR, week, 'approval.json');
  return existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : null;
}

function _setStatus(postId, status) {
  const week = currentWeek();
  const weekDir = join(QUEUE_DIR, week);
  const file = join(weekDir, `${postId}.json`);
  if (!existsSync(file)) throw new Error(`Post not found: ${postId}`);
  const post = JSON.parse(readFileSync(file, 'utf8'));
  post.status = status;
  post.updated = new Date().toISOString();
  writeFileSync(file, JSON.stringify(post, null, 2));
  _syncApproval(week, weekDir);
  return post;
}

function _syncApproval(week, weekDir) {
  const posts = readdirSync(weekDir)
    .filter(f => f.endsWith('.json') && f !== 'approval.json')
    .map(f => JSON.parse(readFileSync(join(weekDir, f), 'utf8')));

  const counts = posts.reduce((acc, p) => {
    acc.total++;
    acc[p.status] = (acc[p.status] || 0) + 1;
    return acc;
  }, { total: 0, pending: 0, approved: 0, skipped: 0, posted: 0 });

  const file = join(weekDir, 'approval.json');
  const tmp = file + '.tmp';
  writeFileSync(tmp, JSON.stringify({ week, ...counts, updated: new Date().toISOString() }, null, 2));
  renameSync(tmp, file);
}

function currentWeek() {
  const now = new Date();
  const jan4 = new Date(now.getFullYear(), 0, 4);
  const week = Math.ceil(((now - jan4) / 86400000 + jan4.getDay() + 1) / 7);
  return `${now.getFullYear()}-W${String(week).padStart(2, '0')}`;
}
