# Source → model review (2026-09-15)

This record is AI static review of the actual supplied source files, not execution, an automated parser result or an independent blind forward test. The implementation task reread all four files, compared the inherited models to the code, and revised the retry model into three linked pages. `tests/test_render.py` tests exports separately and does not import these source programs.

## Decision: `shipping_cost`

Read `source/decision.py:1–6`. Under ordinary numeric total and boolean member:

- `total < 0` → `return None`, no later membership test.
- Nonnegative total and (`member` or `total >= 100`) → `return 0`.
- Otherwise → `return 8`.

The combined OR is a deliberate summary of side-effect-free ordinary-value checks; overloaded operators/truthiness are outside the stated assumption. All three exits and both conditions match the English model.

## Retry: `fetch_first`

Read `source/retry.py:1–16`; inspect the `outer`, `attempts`, `body` pages together. No client/audit implementation was supplied.

| Static path | Model transfer |
|---|---|
| No next key | `outer:next` → `outer:none` (line 16) |
| Falsy key | `outer:empty` → `outer:next`; continue advances outer iterator |
| Truthy key | `outer:inner` → `attempts:entry`, attempt 0 then condition |
| Fetch returns None | `body:result` → pending break → audit → resume → `attempts:break` → `outer:next` |
| Fetch returns non-None | pending return → audit → resume → `attempts:return` → `outer:result` |
| Timeout at attempt 0 or 1 | pending retry → audit → resume → increment → `attempts:check` |
| Timeout at attempt 2 | pending re-raise → audit → resume → `attempts:raise` → `outer:error` |
| Fetch raises another exception | pending propagation → audit → resume → raise exit |
| Audit raises on any pending path | `body:override`; new exception replaces pending return/break/retry/error |

Normal inner-loop exhaustion is displayed as a structural exit but explicitly marked unreachable under this implementation: attempt 2 cannot complete normally into a fourth iteration. `attempt += 1`/condition and pending transfers are semantic expansions of Python iteration/cleanup, not new source statements/variables. Iterator and truthiness protocol internals, nontermination, process termination and interpreter failures are not expanded. External `client.fetch` and `audit` internals remain unknown.

No direct pending return/break/raise bypasses audit. Every retry back edge reaches the condition after the increment. Break is distinct from continue and normal exhaustion.

## Cross-file call: `prepare` → `normalize`

Read `source/service.py:1–9` and `source/validation.py:1–7`.

- `prepare:normalize` at service line 5 enters `normalize:entry`.
- Non-string → None; stripped empty string → None; otherwise lowercase value. Each exit links back to prepare, with the continuation explicitly labeled `prepare:valid` (service line 6 after assignment).
- None → invalid return; other value → `gateway.submit(item)`.
- Gateway normal return → sent status/receipt; gateway exception → propagate to caller. Implementation unavailable, no invented submission success.

Assume ordinary builtin string behavior; subclass overrides of strip/lower and interpreter failures are not expanded. The examples demonstrate small linked subgraphs and source spans, not arbitrary-codebase completeness.

## Untested behavior scope

Concurrency/waiting, recursion, language-specific cleanup beyond Python, massive repositories and other source languages have written analysis guidance but no end-to-end source→model fixture here. Host interoperability beyond the implementation environment and PDF export are not certified.
