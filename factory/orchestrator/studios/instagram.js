import { Studio } from './base.js';
import { callAgentJSON } from '../agent.js';
import { emitter } from '../events.js';

export class InstagramStudio extends Studio {
  constructor() { super('Instagram Studio', 'instagram'); }

  async generate(atoms, persona, researchContext = '') {
    emitter.emit('studio:start', { studio: this.name, platform: this.platform });

    const base = [
      `## Content Atoms\n${JSON.stringify(atoms, null, 2)}`,
      `## Persona\nName: ${persona.name}\nVoice: ${JSON.stringify(persona.voice)}\nTopics: ${persona.topics?.primary?.join(', ')}`,
      researchContext ? `## Research Context\n${researchContext}` : null,
    ].filter(Boolean).join('\n\n');

    // Carousel + reel in parallel
    const [carousel, reel] = await Promise.all([
      callAgentJSON(this.prompt, base + '\n\nGenerate a CAROUSEL — 7-10 slides. Each slide: one punchy point. Include cover text, slide texts, visual notes, caption (under 2200 chars), hashtags.', {
        agentName: 'ig-carousel', maxTokens: 2500, temperature: 0.75,
      }),
      callAgentJSON(this.prompt, base + '\n\nGenerate a REEL SCRIPT — hook in first 3s, 15-30s body, CTA. Include text overlay timing and caption.', {
        agentName: 'ig-reel', maxTokens: 1500, temperature: 0.8,
      }),
    ]);

    const output = {
      platform: this.platform,
      contentType: 'instagram',
      content: { carousel, reel },
      metadata: { generatedAt: new Date().toISOString(), brief: atoms.hook },
    };

    emitter.emit('studio:done', { studio: this.name, platform: this.platform });
    return output;
  }
}
