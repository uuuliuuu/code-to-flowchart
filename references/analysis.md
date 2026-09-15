# Static analysis and coverage

## Scope and evidence

Start with the user's input, not a repository requirement. For pasted code, save or identify a stable virtual file such as `pasted/input.py` and number from 1. For files, use repository-relative paths and one-based inclusive line spans. Record the source revision/hash in coverage when available. Source changes invalidate earlier mappings.

Trace available local callees beyond the entry point. Prefer a single readable page with separate sections for independent entries; use separate pages only when readability requires it or the user requests them. Never connect unrelated entries into a fictitious sequence. Summarize primitive operations only under explicit assumptions (for example ordinary numeric values rather than overloaded comparison). Document missing modules, reflection, callbacks, dependency injection and external services as unresolved boundaries with known inputs/outputs and possible failure exits. Do not infer remote success.

## Execution invariants

- Decisions: label each branch with its source condition, including short-circuit evaluation when calls or side effects make it significant. Early returns terminate that function, subject to cleanup.
- Loops: show initial state, condition/iterator advance, body and exits. A `while` continue returns to its condition; a `for` continue performs the next iteration step. A C-style `for` continue goes through its update. `break` leaves only its target loop; distinguish normal exhaustion and language-specific loop `else` behavior. Label back edges and route them outside nodes.
- Exceptions: label which operation/condition throws, what handler matches, and which failures propagate. Do not route all errors to a nearby catch indiscriminately.
- Cleanup: pending return, break, continue or exception passes through applicable `finally`/defer/resource cleanup before resuming. Cleanup can override that pending transfer in languages that allow it. A synthetic pending-transfer node is a diagram convention, not a source variable. Keep its alternatives conditional so paths cannot be mixed.
- Calls: identify caller page/node, callee entry and return continuation. Multiple call sites have different continuations; duplicate detail for readability or enumerate the mapping. Detail links navigate; they do not themselves mean a call or return. Propagated exceptions need their caller destination too.
- Recursion: show the base condition, recursive call reference and return continuation, without infinite expansion. Mutually recursive functions require a cycle of explicit references.
- Concurrency: an exclusive branch selects a path; a fork starts independent tasks only if the code actually schedules them. `await` suspends the current coroutine until the awaited operation completes; it alone does not establish a parallel fork. Synchronous calls block their calling flow; an async function call may merely create a coroutine. Show task creation separately from wait-all, wait-any, timeout, cancellation and error aggregation. A join must state what it waits for. Do not invent ordering between concurrent branches or equate thread concurrency with guaranteed simultaneous execution.

Concurrency/recursion guidance is language-sensitive and has no supplied end-to-end behavior fixture in v1. Check the source language semantics and disclose unverified behavior rather than extending the Python examples by analogy.

## Large inputs: bounded chunks

1. Inventory candidate entries and available files without claiming they are already read.
2. Maintain an overall view and a coverage ledger: `read`, `unread`, `unknown`, `status`, plus `chunks`, `call_sites`, `assumptions` as needed. Analysis chunks are not automatically separate diagram pages. Combine their flows on one readable page when practical; add overview/detail pages only when needed for readability or requested by the user.
3. For each chunk record stable id, entry/caller, files and spans read, completed diagram ids, unresolved calls, next work and status (pending/partial/complete). Expand one reachable call boundary at a time.
4. Record caller diagram/node, source line, callee diagram/entry and `return_to` for every expanded call. Verify both ends after editing a chunk. Preserve the ledger when continuing in another session.
5. Stop expansion when the requested scope or resource budget is reached. Deliver the overview plus completed details, with unread chunks visibly pending and unknown boundaries explicitly marked. Do not hide omitted callees inside a “complete” process node.

The cross-file example demonstrates two source files and reciprocal page references; retry demonstrates three linked semantic detail pages. These validate small-scale linking, not arbitrary-size analysis, automatic chunking or repository-wide completeness.
