import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { callAgentJSON } from './agent.js';
import { emitter } from './events.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const PROMPT = readFileSync(join(__dir, '../prompts/atoms.md'), 'utf8');

/**
 * Decompose a creative brief into reusable content atoms.
 * Each studio receives these atoms as raw material.
 */
export async function decomposeToAtoms(brief, researchContext = '') {
  emitter.emit('atoms:start', { brief: brief.slice(0, 120) });

  const parts = [`## Creative Brief\n${brief}`];
  if (researchContext) parts.push(`## Research Context\n${researchContext}`);

  const atoms = await callAgentJSON(PROMPT, parts.join('\n\n'), {
    agentName: 'atoms',
    maxTokens: 1500,
    temperature: 0.4,
  });

  emitter.emit('atoms:done', { atoms });
  return atoms;
}
