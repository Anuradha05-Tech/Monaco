# Resume Talking Points & Interview Prep: MONACO

Use this document to prepare for interviews. It outlines the architectural decisions, debugging stories, and systems engineering details of the MONACO platform.

---

## Resume Bullet Point Variants

### Option 1: AI / LLM Engineering Focused
> Built a non-linear, multi-agent code review pipeline using **LangGraph**, orchestrating concurrent static analysis, data-flow tracking, and LLM analysis. Reduced API costs and LLM hallucinations by implementing a strict dual-layer validator that maps LLM outputs to a deterministic JSON schema and validates findings against local AST coordinates before publication.

### Option 2: Security & Static Analysis Focused
> Designed and built a hybrid code review engine combining AST-based static heuristics and taint propagation tracking with LLM analysis. Authored custom AST security rules to detect high-risk functions and command injection vulnerabilities, and implemented cross-commit deduplication using custom HTML metadata comment markers to prevent duplicate reporting on GitHub pull requests.

### Option 3: Systems & Software Engineering Focused
> Architected an idempotent PR review system in Python that processes pull request diffs, resolves import dependencies, and posts targeted inline comments to GitHub. Built a highly optimized parallel fan-out execution model that concurrent-processes security, performance, and code quality agents, reducing wall-clock latency to the duration of the slowest single analysis thread.

---

## The Real Debugging Story: The Evolution of Finding Deduplication

When asked, **"Tell me about a difficult bug you had to solve,"** use this chronicle of MONACO's deduplication system. It demonstrates analytical debugging, moving from quick patches to root-cause structural engineering.

### The Problem Space
In MONACO, code reviews must be **idempotent**. If the system runs multiple times against a PR, or if a developer pushes a new commit, MONACO should not re-post comments for existing bugs, nor double-post when both the static AST analyzer and the AI review engine flag the same issue on the same line.

### Failure 1: The Validator Bypass (Keyword Drift)
* **The Symptom:** During early testing, duplicate comments were being posted on GitHub.
* **The Root Cause:** The validation layer compared the AI's descriptive message with static rules using simple keyword matching. Minor rephrasings by the LLM (e.g., using "subprocess call" instead of "subprocess run") broke the keyword list.
* **The Diagnostic Action:** Wrote a diagnostic script that simulated raw LLM prose outputs and ran them against the validator, confirming that any minor synonym drift caused the validator to assume the AI finding was new.
* **The Fix:** Created a structured system prompt requiring the LLM to output a fixed `rule_category`.

### Failure 2: The Security Agent Leak (Context Drift)
* **The Symptom:** The newly introduced `SecurityAgent` was wrapping the static analyzer's output but began marking general code quality issues (like function complexity or length) as "security" findings.
* **The Root Cause:** The agent's cleanup filter relied on keyword-exclusion lists to strip out non-security findings from the static analyzer. Because the static analyzer changed its output phrasing, the exclusion check failed to match, and quality findings leaked into the security list.
* **The Diagnostic Action:** Created a test harness verifying the filtering logic against raw analyzer data.
* **The Fix:** Modified the agent's LLM call to accept a strict security-focused prompt override, and refactored the analyzer filter to use structural properties (`rule_id` prefixes like `SEC` and `FLOW` and `category == "security"`) as the primary gate, keeping keywords only as a secondary safety net.

### Failure 3: The Unicode & Over-Merge Mismatch (Semantic Matching)
* **The Symptom:** Two distinct bugs occurred during cross-commit deduplication:
  1. A hardcoded secret was posted twice on a new commit.
  2. Two distinct hardcoded secrets on adjacent lines (line 7 `API_KEY`, line 8 `SECRET_TOKEN`) were merged into one comment, leading to silent data loss.
* **The Root Cause:** 
  1. The LLM outputted a Unicode non-breaking hyphen (`Hard\u2011coded`), which bypassed the keyword-matching fallback.
  2. Because both findings shared `rule_id="SEC002"` and were within `LINE_DISTANCE = 3`, the deduplicator merged them without checking if they were actually about the same variable.
* **The Diagnostic Action:** Wrote `debug_sec002_mismatch.py` and `debug_over_merge.py` against the real GitHub API to print the exact repr of the comments. Identified the `\u2011` character and verified the math on the line distance.
* **The Fix:** 
  * Implemented NFKC Unicode normalization and regex stripping of all dash variants in the fallback text checker.
  * Added `variable_name` to the `Finding` model and LLM prompts.
  * Updated `are_duplicates()` to extract the variable name from both findings and verify they match (case-insensitive). If they differ, the merge is rejected.

---

## Likely Interview Questions & Answers

### 1. "Why did you use LangGraph instead of a simple sequential script?"
> **Answer:** 
> A sequential script forces a linear execution path. In code review, we need non-linear execution. 
> For example, if a PR contains no Python files, we must skip analysis entirely. 
> Furthermore, if validation rejects too many LLM findings (high noise), we want to divert the graph to a human-in-the-loop review state. 
> LangGraph allowed us to model this state machine explicitly. It also cleanly handles parallel execution (fanning out to our three agents and fanning back in) out of the box, keeping the code modular and thread-safe.

### 2. "Your data-flow analyzer is described as 'intra-procedural'. What does that mean, and how would you make it inter-procedural?"
> **Answer:** 
> Currently, the data-flow analyzer processes statements sequentially within a single file's top level or function bodies. If a tainted variable is passed as an argument to another function, the analyzer loses track of it.
> To make it inter-procedural, we would need to construct a Call Graph of the repository. When a function call is encountered, we would map the arguments to the target function's parameter variables, analyze the target function's AST under that tainted context, and track the return value. This is a significant increase in complexity that requires resolving imports across the entire repository.

### 3. "How does comment deduplication handle file edits that shift line numbers?"
> **Answer:** 
> This is a known limitation. Currently, the comment identifier is a tuple of `(file, line, rule_id)`. If lines are added above the finding, the line number shifts, and the deduplicator will treat it as a new finding.
> To fix this, I would implement **AST-based semantic fingerprinting** instead of raw line numbers. By generating a path hash from the AST node where the finding occurred (e.g., `Module/Class/Function/Assign[target="API_KEY"]`), the finding's identity remains stable even if lines of code are added or removed around it.

### 4. "What would you do differently if you were rebuilding MONACO from scratch?"
> **Answer:**
> I would have started with a structured JSON output schema and rule mapping from day one. I spent significant time debugging regexes and keyword matchers for LLM responses because I initially treated the LLM as a prose-generating black box. Constraining the model at the input and output boundaries using strict schemas and mapping them to structured `rule_id` keys makes the downstream pipeline vastly more reliable.
