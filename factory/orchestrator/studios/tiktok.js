import { Studio } from './base.js';
import { callAgentJSON } from '../agent.js';
import { emitter } from '../events.js';

export class TikTokStudio extends Studio {
  constructor() { super('TikTok Studio', 'tiktok'); }

  async generate(atoms, persona, researchContext = '') {
    emitter.emit('studio:start', { studio: this.name, platform: this.platform });

    const base = [
      `## Content Atoms\n${JSON.stringify(atoms, null, 2)}`,
      `## Persona\nName: ${persona.name}\nVoice: ${JSON.stringify(persona.voice)}\nTopics: ${persona.topics?.primary?.join(', ')}`,
      researchContext ? `## Research Context\n${researchContext}` : null,
    ].filter(Boolean).join('\n\n');

    // Hooks and scripts run in parallel — hooks are a dedicated sub-pass for higher variety
    const [hooks, scripts] = await Promise.all([
      callAgentJSON(this.prompt, base + '\n\nGenerate HOOK_VARIANTS only — 5 distinct hooks, each under 8 words. Focus on maximum scroll-stop power.', {
        agentName: 'tiktok-hooks', maxTokens: 800, temperature: 0.9,
      }),
      callAgentJSON(this.prompt, base + '\n\nGenerate SCRIPTS only — 30s, 60s, 90s versions with text overlays, caption, and hashtags.', {
        agentName: 'tiktok-scripts', maxTokens: 2500, temperature: 0.75,
      }),
    ]);

    const output = {
      platform: this.platform,
      contentType: 'tiktok',
      content: { hook_variants: hooks.hook_variants || hooks, ...scripts },
      metadata: { generatedAt: new Date().toISOString(), brief: atoms.hook },
    };

    emitter.emit('studio:done', { studio: this.name, platform: this.platform });
    return output;
  }
}
