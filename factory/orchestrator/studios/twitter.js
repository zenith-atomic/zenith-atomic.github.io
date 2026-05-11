import { Studio } from './base.js';
import { callAgentJSON } from '../agent.js';
import { emitter } from '../events.js';

export class TwitterStudio extends Studio {
  constructor() { super('X Studio', 'twitter'); }

  async generate(atoms, persona, researchContext = '') {
    emitter.emit('studio:start', { studio: this.name, platform: this.platform });

    const base = [
      `## Content Atoms\n${JSON.stringify(atoms, null, 2)}`,
      `## Persona\nName: ${persona.name}\nVoice: ${JSON.stringify(persona.voice)}\nTopics: ${persona.topics?.primary?.join(', ')}`,
      researchContext ? `## Research Context\n${researchContext}` : null,
    ].filter(Boolean).join('\n\n');

    // Thread + singles in parallel
    const [thread, singles] = await Promise.all([
      callAgentJSON(this.prompt, base + '\n\nGenerate a THREAD — 8-15 tweets, each under 280 chars, each must stand alone AND advance narrative.', {
        agentName: 'x-thread', maxTokens: 2500, temperature: 0.75,
      }),
      callAgentJSON(this.prompt, base + '\n\nGenerate SINGLES — 3 standalone tweets (different angles), each under 280 chars. Also suggest best posting time.', {
        agentName: 'x-singles', maxTokens: 1000, temperature: 0.8,
      }),
    ]);

    const output = {
      platform: this.platform,
      contentType: 'twitter',
      content: { thread, ...singles },
      metadata: { generatedAt: new Date().toISOString(), brief: atoms.hook },
    };

    emitter.emit('studio:done', { studio: this.name, platform: this.platform });
    return output;
  }
}
