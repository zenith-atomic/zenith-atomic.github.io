/**
 * Pursuit Runner — executes a single research pursuit.
 * Searches the web, synthesizes findings via LLM, saves to findings/.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';
import { callAgent } from '../orchestrator/agent.js';
import { emitter } from '../orchestrator/events.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const FACTORY = join(__dir, '..');
const RESEARCH_DIR = __dir;
const FINDINGS_DIR = join(RESEARCH_DIR, 'findings');
const PURSUIT_PROMPT = readFileSync(join(FACTORY, 'prompts/research/pursuit.md'), 'utf8');
const SYNTHESIS_PROMPT = readFileSync(join(FACTORY, 'prompts/research/synthesis.md'), 'utf8');

/**
 * Execute a pursuit by ID.
 * Reads config from pursuits/{id}.yml, runs research, saves finding.
 */
export async function runPursuit(id) {
  const config = loadPursuitConfig(id);
  const runDate = new Date().toISOString().split('T')[0];

  emitter.emit('pursuit:start', { id, name: config.name });

  const findingDir = join(FINDINGS_DIR, id);
  mkdirSync(findingDir, { recursive: true });

  // Build research prompt
  const userMsg = [
    `## Pursuit: ${config.name}`,
    `## Query\n${config.query}`,
    `## Focus Areas\n${(config.focus || []).join('\n')}`,
    `## Sources to prioritize\n${(config.sources || ['web', 'twitter', 'youtube']).join(', ')}`,
    `## Depth: ${config.depth || 'standard'}`,
    `\nToday: ${runDate}. Research what is current and trending NOW. Be specific, cite examples.`,
  ].join('\n\n');

  // Run research agent
  const findings = await callAgent(PURSUIT_PROMPT, userMsg, {
    agentName: `pursuit-${id}`,
    maxTokens: 3000,
    temperature: 0.4,
    model: process.env.FACTORY_RESEARCH_MODEL || process.env.FACTORY_MODEL || 'gpt-4.1',
  });

  // Synthesize to structured summary
  const summary = await callAgent(SYNTHESIS_PROMPT, `## Raw Findings\n${findings}`, {
    agentName: `synthesis-${id}`,
    maxTokens: 1500,
    temperature: 0.3,
  });

  const outFile = join(findingDir, `${runDate}.md`);
  const latestFile = join(findingDir, 'latest.md');

  const content = [
    `---`,
    `pursuit: ${id}`,
    `name: ${config.name}`,
    `date: ${runDate}`,
    `---`,
    '',
    summary,
  ].join('\n');

  writeFileSync(outFile, content);
  writeFileSync(latestFile, content);

  emitter.emit('pursuit:done', { id, name: config.name, file: outFile });

  return { id, name: config.name, date: runDate, file: outFile, summary };
}

export function loadPursuitConfig(id) {
  const file = join(RESEARCH_DIR, 'pursuits', `${id}.yml`);
  if (!existsSync(file)) throw new Error(`Pursuit config not found: ${id}`);
  return yaml.load(readFileSync(file, 'utf8'));
}

export function listPursuitConfigs() {
  const dir = join(RESEARCH_DIR, 'pursuits');
  if (!existsSync(dir)) return [];
  const files = readdirSync(dir).filter(f => f.endsWith('.yml'));
  return files.map(f => {
    const id = f.replace('.yml', '');
    try { return { id, ...yaml.load(readFileSync(join(dir, f), 'utf8')) }; }
    catch { return { id, error: 'parse error' }; }
  });
}
