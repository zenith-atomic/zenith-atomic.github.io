---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

## The Iron Law
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

## Red-Green-Refactor

**RED** — Write failing test
- One minimal test showing what should happen
- Clear name, tests real behavior, one thing

**Verify RED** — Watch it fail (MANDATORY)
```bash
npm test / pytest / cargo test
```
Confirm: test fails (not errors), failure message is expected

**GREEN** — Minimal code
Write simplest code to pass the test. Don't add features, don't refactor.

**Verify GREEN** — Watch it pass (MANDATORY)
- Test passes, other tests still pass, output pristine

**REFACTOR** — Clean up
After green: remove duplication, improve names, extract helpers. Keep tests green.

## Good Tests
- **Minimal:** One thing. "and" in name? Split it.
- **Clear:** Name describes behavior
- **Shows intent:** Demonstrates desired API, not how it works

## Why Order Matters
Tests-after prove nothing — they pass immediately. Test-first forces you to see the test fail, proving it tests something real.

## Verification Checklist
Before marking work complete:
- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
