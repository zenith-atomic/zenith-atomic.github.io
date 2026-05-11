# Code Quality Reviewer Prompt Template

**Only dispatch after spec compliance review passes.**

Use the code-reviewer.md template from requesting-code-review/.

In addition to standard concerns, check:
- Does each file have one clear responsibility with a well-defined interface?
- Are units decomposed so they can be understood and tested independently?
- Is the implementation following the file structure from the plan?
- Did this implementation create new files that are already large, or significantly grow existing files?

Code reviewer returns: Strengths, Issues (Critical/Important/Minor), Assessment
