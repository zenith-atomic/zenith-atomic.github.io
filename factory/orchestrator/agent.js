import OpenAI from 'openai';
import { emitter } from './events.js';

let _client = null;
function client() {
  if (!_client) _client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  return _client;
}
const DEFAULT_MODEL = process.env.FACTORY_MODEL || 'gpt-4.1';

export async function callAgent(systemPrompt, userMessage, opts = {}) {
  const {
    agentName = 'agent',
    model = DEFAULT_MODEL,
    maxTokens = 4000,
    temperature = 0.7,
    retries = 2,
    responseFormat,
  } = opts;

  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (attempt > 0) await sleep(1000 * 2 ** (attempt - 1));
      emitter.emit('agent:start', { name: agentName, attempt });

      const params = {
        model,
        max_tokens: maxTokens,
        temperature,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userMessage },
        ],
      };
      if (responseFormat) params.response_format = responseFormat;

      const res = await client().chat.completions.create(params);
      const content = res.choices[0].message.content || '';
      emitter.emit('agent:done', { name: agentName, tokens: res.usage?.total_tokens });
      return content;
    } catch (err) {
      lastError = err;
      emitter.emit('agent:error', { name: agentName, attempt, error: err.message });
    }
  }
  throw lastError;
}

export async function callAgentJSON(systemPrompt, userMessage, opts = {}) {
  const raw = await callAgent(systemPrompt, userMessage, {
    ...opts,
    temperature: opts.temperature ?? 0.3,
    responseFormat: { type: 'json_object' },
  });
  try {
    return JSON.parse(raw);
  } catch {
    const match = raw.match(/```(?:json)?\n?([\s\S]+?)\n?```/);
    if (match) return JSON.parse(match[1]);
    throw new Error(`${opts.agentName || 'agent'} returned non-JSON: ${raw.slice(0, 300)}`);
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
