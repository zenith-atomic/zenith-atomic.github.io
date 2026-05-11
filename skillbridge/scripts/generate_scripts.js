#!/usr/bin/env node
/**
 * ContentFactory Script Generator
 * Batch-generates niche-specific short-form video scripts
 * 
 * Usage: node scripts/generate_scripts.js --niche "personal_finance" --count 5
 */

const fs = require('fs');

// Hook frameworks for short-form video
const HOOK_TEMPLATES = {
  stat: [
    "97% of people don't know this about {topic}.",
    "{number} out of {number} {audience} make this mistake with {topic}.",
    "{topic} costs the average {audience} ${number}/month. Here's why.",
    "The {topic} mistake that costs {audience} ${number}/year (easy fix).",
  ],
  question: [
    "Are you making this {topic} mistake?",
    "What if I told you {topic} could {benefit} in {timeframe}?",
    "Does your {topic} actually {problem}? Most do.",
    "Who else struggles with {topic}? (you're not alone)",
  ],
  story: [
    "I helped a {audience} {topic} and the results were insane.",
    "This {audience} was {problem} until they tried this {topic} approach.",
    "3 weeks ago I discovered {topic}. It changed everything.",
    "A client asked me about {topic}. Here's what happened next.",
  ],
  contrast: [
    "{audience} who {action} {topic} vs. those who don't (the gap is real).",
    "Rich {audience} think about {topic} differently. Here's why.",
    "Before and after: how {topic} transformed my {audience}'s results.",
    "What {audience} think {topic} is vs. what it actually is.",
  ],
  countdown: [
    "3 {topic} secrets most {audience} never find out.",
    "5 {topic} mistakes that are costing you {currency}.",
    "The 4-step {topic} system I use with every {audience}.",
    "Top {number} {topic} strategies that actually work for {audience}.",
  ],
};

const NICHE_PROFILES = {
  personal_finance: {
    name: "Personal Finance",
    hookTypes: ["stat", "question", "contrast"],
    bestPostingTimes: "6am-9am EST",
    cpm: 2.50,
    topics: [
      "401k employer match",
      "high-yield savings accounts",
      "credit card debt payoff",
      "automated investing",
      "the 50/30/20 rule",
      "health insurance deductible",
      "tax-loss harvesting",
    ],
    audience: "25-40 year olds",
    cta: "Follow for more financial strategies that actually work.",
    painPoint: "leaving free money on the table",
    benefit: "build wealth faster",
    currency: "$500/month",
    timeframe: "30 days",
    action: "optimize",
  },
  tech_ai: {
    name: "Tech & AI Tools",
    hookTypes: ["stat", "question", "howto"],
    bestPostingTimes: "10am-2pm EST",
    cpm: 2.75,
    topics: [
      "ChatGPT prompts that save 10 hours a week",
      "AI tools for remote workers",
      "automating spreadsheets with AI",
      "best AI writing assistants 2026",
      "no-code automation tools",
    ],
    audience: "professionals and small business owners",
    cta: "Save this post. You'll want to revisit it.",
    painPoint: "wasting hours on tasks AI could do",
    benefit: "save 10+ hours every week",
    currency: "$200/month in recovered time",
    timeframe: "the next week",
    action: "automate",
  },
  fitness: {
    name: "Fitness & Body Transformation",
    hookTypes: ["story", "question", "countdown"],
    bestPostingTimes: "5pm-8pm EST",
    cpm: 1.75,
    topics: [
      "muscle confusion workout principle",
      "intermittent fasting for beginners",
      "home workout with no equipment",
      "pre-workout nutrition timing",
      "post-workout recovery techniques",
    ],
    audience: "people starting their fitness journey",
    cta: "Save this for your next workout.",
    painPoint: "not seeing gym results",
    benefit: "actually transform your body",
    currency: "$300/month gym membership waste",
    timeframe: "the next 90 days",
    action: "commit to",
  },
  productivity: {
    name: "Productivity & High Performance",
    hookTypes: ["stat", "howto", "contrast"],
    bestPostingTimes: "7am-10am EST",
    cpm: 1.85,
    topics: [
      "deep work sessions for creatives",
      "the 2-minute rule for task management",
      "time blocking for entrepreneurs",
      "morning routine that maximizes output",
      "batching similar tasks for efficiency",
    ],
    audience: "busy professionals",
    cta: "Save this. Come back to it when you need it.",
    painPoint: "constant distraction and overwhelm",
    benefit: "get twice as much done in half the time",
    currency: "10 hours/week",
    timeframe: "the next week",
    action: "implement",
  },
  entrepreneurship: {
    name: "Entrepreneurship & Side Hustles",
    hookTypes: ["story", "stat", "question"],
    bestPostingTimes: "12pm-3pm EST",
    cpm: 2.25,
    topics: [
      "pricing your services as a freelancer",
      "finding your first 10 clients on LinkedIn",
      "outreach templates that actually get replies",
      "building recurring revenue as a consultant",
      "the lean startup approach to testing ideas",
    ],
    audience: "aspiring entrepreneurs and freelancers",
    cta: "Follow for more business strategies that work.",
    painPoint: "trading time for money with no leverage",
    benefit: "build multiple income streams",
    currency: "$5K/month on the side",
    timeframe: "the next 90 days",
    action: "build",
  },
};

// Format a template string with random values
function fillTemplate(template, vars) {
  return template
    .replace(/{number}/g, () => String([99, 87, 76, 65, 54, 43, 32, 21, 10][Math.floor(Math.random() * 9)]))
    .replace(/{audience}/g, () => vars.audience)
    .replace(/{topic}/g, () => vars.topic)
    .replace(/{benefit}/g, () => vars.benefit)
    .replace(/{timeframe}/g, () => vars.timeframe || "30 days")
    .replace(/{problem}/g, () => vars.painPoint)
    .replace(/{action}/g, () => vars.action || "master")
    .replace(/{currency}/g, () => vars.currency)
    .replace(/{time}/g, () => vars.time || "30 days");
}

// Generate a single script
function generateScript(niche, topic, hookType, scriptNumber) {
  const profile = NICHE_PROFILES[niche];
  if (!profile) return null;

  const templates = HOOK_TEMPLATES[hookType] || HOOK_TEMPLATES.question;
  const template = templates[Math.floor(Math.random() * templates.length)];

  const vars = {
    topic,
    audience: profile.audience,
    benefit: profile.benefit,
    painPoint: profile.painPoint,
    currency: profile.currency,
    timeframe: profile.timeframe,
    action: profile.action,
  };

  const hook = fillTemplate(template, vars);

  const angles = [
    `Here's exactly how to ${vars.topic} — step by step.`,
    `The truth about ${vars.topic} that nobody talks about.`,
    `If you're doing ${vars.topic} wrong, stop now. Here's the fix.`,
    `Everything you need to know about ${vars.topic} in under 60 seconds.`,
    `The ${vars.topic} mistake I see every week (stop doing this).`,
  ];

  const body = angles[scriptNumber % angles.length];
  const cta = profile.cta;

  return {
    hookType,
    hook,
    body,
    cta,
    estimatedDuration: "45-60 seconds",
    postingTime: profile.bestPostingTimes,
    targetCPM: profile.cpm,
    topic,
  };
}

// Generate batch of scripts
function generateBatch(niche, count = 10, hookTypes = null) {
  const profile = NICHE_PROFILES[niche];
  if (!profile) {
    console.error(`Unknown niche: ${niche}`);
    console.error(`Available niches: ${Object.keys(NICHE_PROFILES).join(', ')}`);
    process.exit(1);
  }

  const hooks = hookTypes || profile.hookTypes;
  const scripts = [];

  for (let i = 0; i < count; i++) {
    const hookType = hooks[i % hooks.length];
    const topic = profile.topics[i % profile.topics.length];
    scripts.push(generateScript(niche, topic, hookType, i));
  }

  return scripts;
}

// Module exports
module.exports = { generateScript, generateBatch, NICHE_PROFILES };

// CLI entry point
if (require.main === module) {
  const args = process.argv.slice(2);
  const nicheIndex = args.indexOf('--niche');
  const countIndex = args.indexOf('--count');
  const hooksIndex = args.indexOf('--hooks');
  const outputIndex = args.indexOf('--output');

  const niche = nicheIndex !== -1 ? args[nicheIndex + 1] : 'personal_finance';
  const count = countIndex !== -1 ? parseInt(args[countIndex + 1]) : 10;
  const hookTypes = hooksIndex !== -1 ? args[hooksIndex + 1].split(',') : null;
  const outputFile = outputIndex !== -1 ? args[outputIndex + 1] : null;

  const scripts = generateBatch(niche, count, hookTypes);

  const output = {
    niche,
    profile: NICHE_PROFILES[niche],
    generatedAt: new Date().toISOString(),
    count: scripts.length,
    scripts,
  };

  const json = JSON.stringify(output, null, 2);

  if (outputFile) {
    fs.writeFileSync(outputFile, json);
    console.log(`Wrote ${scripts.length} scripts to ${outputFile}`);
  } else {
    console.log(json);
  }
}
