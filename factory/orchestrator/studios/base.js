import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { callAgentJSON } from '../agent.js';
import { emitter } from '../events.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const PROMPTS_DIR = join(__dir, '../../prompts/studios');

export class Studio {
  constructor(name, platform) {
    this.name = name;
    this.platform = platform;
    this.prompt = readFileSync(join(PROMPTS_DIR, `${platform}.md`), 'utf8');
  }

  async generate(atoms, persona, researchContext = '') {
    emitter.emit('studio:start', { studio: this.name, platform: this.platform });

    const userMsg = buildUserMessage(atoms, persona, researchContext);

    try {
      const raw = await callAgentJSON(this.prompt, userMsg, {
        agentName: this.name,
        maxTokens: 4000,
        temperature: 0.75,
      });

      const output = {
        platform: this.platform,
        contentType: raw.contentType || this.platform,
        content: raw,
        metadata: {
          generatedAt: new Date().toISOString(),
          brief: atoms.hook,
        },
      };

      emitter.emit('studio:done', { studio: this.name, platform: this.platform });
      return output;
    } catch (err) {
      emitter.emit('studio:error', { studio: this.name, platform: this.platform, error: err.message });
      throw err;
    }
  }
}

function buildUserMessage(atoms, persona, researchContext) {
  const parts = [
    `## Content Atoms\n${JSON.stringify(atoms, null, 2)}`,
    `## Persona\nName: ${persona.name}\nVoice: ${JSON.stringify(persona.voice)}\nTopics: ${persona.topics?.primary?.join(', ')}\nAudience: ${persona.audience?.who}`,
  ];
  if (researchContext) parts.push(`## Research Context\n${researchContext}`);
  return parts.join('\n\n');
}
