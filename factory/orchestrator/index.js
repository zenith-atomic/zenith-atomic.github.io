#!/usr/bin/env node
/**
 * Factory Orchestrator CLI + module entry point.
 *
 * CLI usage:
 *   node index.js brief "<text>" [--platforms youtube,tiktok,twitter,instagram]
 *   node index.js status [runId]
 *   node index.js queue
 */
import { orchestrate } from './director.js';
import { listRuns, getState } from './state.js';
import { getQueue, approve, skip, getApproval } from './queue.js';
import { emitter } from './events.js';

// Wire up console logging for all emitter events
emitter.on('run:start',    e => log(`▶  Run ${e.runId} started`));
emitter.on('atoms:start',  e => log(`   Decomposing brief → atoms`));
emitter.on('atoms:done',   () => log(`   ✓ Atoms ready`));
emitter.on('studio:start', e => log(`   ● ${e.studio} starting`));
emitter.on('studio:done',  e => log(`   ✓ ${e.studio} done`));
emitter.on('studio:error', e => log(`   ✗ ${e.studio} error: ${e.error}`));
emitter.on('agent:error',  e => log(`   ! agent ${e.name} attempt ${e.attempt} failed: ${e.error}`));
emitter.on('run:done',     e => log(`✓  Run ${e.runId} done — ${e.queuedCount} posts queued`));
emitter.on('run:error',    e => log(`✗  Run ${e.runId} error: ${e.error}`));

function log(msg) { process.stderr.write(msg + '\n'); }

// ─── CLI ────────────────────────────────────────────────────────────────────

const [,, cmd, ...args] = process.argv;

async function main() {
  switch (cmd) {
    case 'brief': {
      const text = args.join(' ').replace(/^["']|["']$/g, '');
      if (!text) { console.error('Usage: node index.js brief "<text>"'); process.exit(1); }

      const platformArg = args.find(a => a.startsWith('--platforms='));
      const platforms = platformArg
        ? platformArg.split('=')[1].split(',')
        : ['youtube', 'tiktok', 'twitter', 'instagram'];

      const result = await orchestrate(text, { platforms });
      console.log(JSON.stringify(result, null, 2));
      break;
    }

    case 'status': {
      const runId = args[0];
      if (runId) {
        console.log(JSON.stringify(getState(runId), null, 2));
      } else {
        const runs = listRuns(10);
        console.log(JSON.stringify(runs.map(r => ({
          id: r.id, phase: r.phase, created: r.created, brief: r.brief?.slice(0, 80),
        })), null, 2));
      }
      break;
    }

    case 'queue': {
      const q = getQueue();
      const approval = getApproval();
      console.log(JSON.stringify({ approval, posts: q }, null, 2));
      break;
    }

    case 'approve': {
      const postId = args[0];
      if (!postId) { console.error('Usage: node index.js approve <postId>'); process.exit(1); }
      console.log(JSON.stringify(approve(postId), null, 2));
      break;
    }

    case 'skip': {
      const postId = args[0];
      if (!postId) { console.error('Usage: node index.js skip <postId>'); process.exit(1); }
      console.log(JSON.stringify(skip(postId), null, 2));
      break;
    }

    default:
      console.error(`Commands: brief "<text>" | status [runId] | queue | approve <id> | skip <id>`);
      process.exit(1);
  }
}

import { resolve } from 'path';
import { fileURLToPath } from 'url';
const _isMain = process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));
if (_isMain) main().catch(err => { console.error(err.message); process.exit(1); });

// Module exports for dashboard integration
export { orchestrate } from './director.js';
export { emitter } from './events.js';
export { listRuns, getState } from './state.js';
export { getQueue, approve, skip, getApproval } from './queue.js';
