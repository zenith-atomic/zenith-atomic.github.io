import { Studio } from './base.js';
import { callAgentJSON } from '../agent.js';
import { emitter } from '../events.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dir = dirname(fileURLToPath(import.meta.url));

export class YouTubeStudio extends Studio {
  constructor() { super('YouTube Studio', 'youtube'); }

  async generate(atoms, persona, researchContext = '') {
    emitter.emit('studio:start', { studio: this.name, platform: this.platform });

    const userMsg = [
      `## Content Atoms\n${JSON.stringify(atoms, null, 2)}`,
      `## Persona\nName: ${persona.name}\nVoice: ${JSON.stringify(persona.voice)}\nTopics: ${persona.topics?.primary?.join(', ')}`,
      researchContext ? `## Research Context\n${researchContext}` : null,
    ].filter(Boolean).join('\n\n');

    // Run long-form + shorts in parallel — two separate sub-calls
    const [longForm, short] = await Promise.all([
      callAgentJSON(this.prompt, userMsg + '\n\nGenerate the LONG_FORM format only.', {
        agentName: 'yt-longform', maxTokens: 3000, temperature: 0.75,
      }),
      callAgentJSON(this.prompt, userMsg + '\n\nGenerate the SHORT format only.', {
        agentName: 'yt-short', maxTokens: 1500, temperature: 0.8,
      }),
    ]);

    const output = {
      platform: this.platform,
      contentType: 'youtube',
      content: { long_form: longForm, short },
      metadata: { generatedAt: new Date().toISOString(), brief: atoms.hook },
    };

    emitter.emit('studio:done', { studio: this.name, platform: this.platform });
    return output;
  }
}
