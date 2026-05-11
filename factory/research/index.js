#!/usr/bin/env node
/**
 * Research Pursuits — CLI + module entry.
 *
 * CLI:
 *   node index.js list
 *   node index.js run <id>
 *   node index.js run-all
 *   node index.js create <id> "<name>" "<query>"
 *   node index.js findings <id> [n]
 *   node index.js context              ← formatted context for studios
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';
import { runPursuit, loadPursuitConfig } from './runner.js';
import { loadIndex, syncIndexFromDisk, runDuePursuits } from './scheduler.js';
import { emitter } from '../orchestrator/events.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const PURSUITS_DIR = join(__dir, 'pursuits');
const FINDINGS_DIR = join(__dir, 'findings');

// Log pursuit events to stderr
emitter.on('pursuit:start', e => process.stderr.write(`▶  Pursuit "${e.name}" (${e.id}) running...\n`));
emitter.on('pursuit:done',  e => process.stderr.write(`✓  Pursuit "${e.name}" done → ${e.file}\n`));
emitter.on('agent:start',   e => process.stderr.write(`   ● ${e.name}\n`));
emitter.on('agent:done',    e => process.stderr.write(`   ✓ ${e.name} (${e.tokens || '?'} tokens)\n`));

// ─── Module exports ──────────────────────────────────────────────────────────

export { runPursuit } from './runner.js';
export { loadIndex, syncIndexFromDisk, runDuePursuits } from './scheduler.js';

/** Get formatted research context string for injection into studio prompts. */
export function getActiveContext(maxChars = 6000) {
  const index = loadIndex();
  const active = (index.pursuits || [])
    .filter(p => p.status === 'active' && p.latestFinding && existsSync(p.latestFinding))
    .slice(0, 6);

  const chunks = active.map(p => {
    try {
      const text = readFileSync(p.latestFinding, 'utf8');
      return `### ${p.name}\n${stripFrontmatter(text).slice(0, 1000)}`;
    } catch { return null; }
  }).filter(Boolean);

  return chunks.join('\n\n').slice(0, maxChars);
}

/** Create a new pursuit config file. */
export function createPursuit(id, name, query, opts = {}) {
  mkdirSync(PURSUITS_DIR, { recursive: true });
  const file = join(PURSUITS_DIR, `${id}.yml`);
  if (existsSync(file)) throw new Error(`Pursuit ${id} already exists`);

  const config = {
    name,
    query,
    focus: opts.focus || [],
    sources: opts.sources || ['web', 'twitter', 'youtube'],
    frequency: opts.frequency || 'daily',
    depth: opts.depth || 'standard',
    notify: opts.notify !== false,
    status: 'active',
    created: new Date().toISOString(),
  };

  writeFileSync(file, yaml.dump(config));
  syncIndexFromDisk();
  return config;
}

function stripFrontmatter(text) {
  return text.replace(/^---[\s\S]*?---\n/, '').trim();
}

// ─── CLI ─────────────────────────────────────────────────────────────────────

const [,, cmd, ...args] = process.argv;

async function main() {
  switch (cmd) {
    case 'list': {
      const index = loadIndex();
      if (!index.pursuits.length) { console.log('No pursuits configured.'); break; }
      for (const p of index.pursuits) {
        const last = p.lastRun ? new Date(p.lastRun).toLocaleDateString() : 'never';
        const status = p.status === 'active' ? '●' : '○';
        console.log(`${status} ${p.id.padEnd(24)} ${p.name.padEnd(36)} freq:${p.frequency.padEnd(8)} last:${last}`);
      }
      break;
    }

    case 'run': {
      const id = args[0];
      if (!id) { console.error('Usage: node index.js run <id>'); process.exit(1); }
      const result = await runPursuit(id);
      console.log(`Done. Saved to: ${result.file}`);
      console.log('\n' + result.summary);
      break;
    }

    case 'run-all':
    case 'run-due': {
      await runDuePursuits();
      break;
    }

    case 'create': {
      const [id, name, query] = args;
      if (!id || !name || !query) {
        console.error('Usage: node index.js create <id> "<name>" "<query>"');
        process.exit(1);
      }
      const config = createPursuit(id, name, query);
      console.log(`Created pursuit: ${id}`);
      console.log(yaml.dump(config));
      break;
    }

    case 'findings': {
      const id = args[0];
      const n = parseInt(args[1]) || 1;
      if (!id) { console.error('Usage: node index.js findings <id> [n]'); process.exit(1); }

      const dir = join(FINDINGS_DIR, id);
      if (!existsSync(dir)) { console.log('No findings yet.'); break; }

      const files = readdirSync(dir)
        .filter(f => f !== 'latest.md' && f.endsWith('.md'))
        .sort().reverse().slice(0, n);

      for (const f of files) {
        console.log(`\n${'─'.repeat(60)}`);
        console.log(readFileSync(join(dir, f), 'utf8'));
      }
      break;
    }

    case 'context': {
      console.log(getActiveContext());
      break;
    }

    default:
      console.error('Commands: list | run <id> | run-due | create <id> "<name>" "<query>" | findings <id> [n] | context');
      process.exit(1);
  }
}

// Only run CLI when this file is the entry point
import { resolve } from 'path';
const isMain = process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));
if (isMain) main().catch(err => { console.error(err.message); process.exit(1); });
