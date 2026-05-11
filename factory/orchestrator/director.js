import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';
import { decomposeToAtoms } from './atoms.js';
import { createRun, updateRun } from './state.js';
import { addToQueue } from './queue.js';
import { emitter } from './events.js';
import { YouTubeStudio } from './studios/youtube.js';
import { TikTokStudio } from './studios/tiktok.js';
import { TwitterStudio } from './studios/twitter.js';
import { InstagramStudio } from './studios/instagram.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const FACTORY = join(__dir, '..');
const CONFIG = join(FACTORY, 'config');
const RESEARCH_DIR = join(FACTORY, 'research');

const STUDIOS = [
  new YouTubeStudio(),
  new TikTokStudio(),
  new TwitterStudio(),
  new InstagramStudio(),
];

/**
 * Run a creative brief through all platform studios in parallel.
 * Returns runId + array of queued post IDs.
 */
export async function orchestrate(brief, opts = {}) {
  const { platforms = ['youtube', 'tiktok', 'twitter', 'instagram'] } = opts;

  const runId = createRun(brief);
  emitter.emit('run:start', { runId, brief: brief.slice(0, 120) });

  try {
    // Load persona
    const persona = loadPersona();

    // Load research context
    const researchContext = loadResearchContext();

    updateRun(runId, { phase: 'atoms' });
    const atoms = await decomposeToAtoms(brief, researchContext);
    updateRun(runId, { phase: 'studios', atoms });

    // Run selected studios in parallel
    const activeStudios = STUDIOS.filter(s => platforms.includes(s.platform));
    const results = await Promise.allSettled(
      activeStudios.map(studio => studio.generate(atoms, persona, researchContext))
    );

    // Collect successes, log failures
    const queuedIds = [];
    const studioResults = {};

    for (let i = 0; i < results.length; i++) {
      const studio = activeStudios[i];
      const result = results[i];

      if (result.status === 'fulfilled') {
        const postId = addToQueue(result.value, runId);
        queuedIds.push(postId);
        studioResults[studio.platform] = { status: 'done', postId };
      } else {
        studioResults[studio.platform] = { status: 'error', error: result.reason?.message };
        emitter.emit('studio:error', {
          studio: studio.name,
          platform: studio.platform,
          error: result.reason?.message,
        });
      }
    }

    updateRun(runId, { phase: 'done', studioResults, queuedIds });
    emitter.emit('run:done', { runId, queuedCount: queuedIds.length });

    return { runId, queuedIds, studioResults };
  } catch (err) {
    updateRun(runId, { phase: 'error', error: err.message });
    emitter.emit('run:error', { runId, error: err.message });
    throw err;
  }
}

function loadPersona() {
  const file = join(CONFIG, 'persona.yml');
  return yaml.load(readFileSync(file, 'utf8'));
}

function loadResearchContext(maxChars = 6000) {
  try {
    const indexFile = join(RESEARCH_DIR, 'pursuit_index.json');
    if (!existsSync(indexFile)) return '';

    const index = JSON.parse(readFileSync(indexFile, 'utf8'));
    const active = (index.pursuits || [])
      .filter(p => p.status === 'active' && p.latestFinding)
      .slice(0, 5);

    const chunks = active.map(p => {
      try {
        const text = readFileSync(p.latestFinding, 'utf8');
        return `### ${p.name}\n${text.slice(0, 1200)}`;
      } catch { return null; }
    }).filter(Boolean);

    return chunks.join('\n\n').slice(0, maxChars);
  } catch { return ''; }
}

// existsSync not imported in this scope — pull it in
import { existsSync } from 'fs';
