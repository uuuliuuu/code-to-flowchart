# Verification: keep two evidence tracks

## Source → model (AI static review)

Read the actual input source without importing/executing it. Record entry, assumptions and line spans. Trace each branch and return; check loop advance/condition destinations, break/continue/exhaustion, throwing operations, handler matches and cleanup. Map each expanded callee's entry and exits to the originating call/continuation. Record unresolved external behavior and unread chunks. Manually trace representative paths, including failure/early exits. A model fixture being rendered successfully is not evidence that AI extracted it correctly.

For the bundled examples, `examples/semantic-review.md` records the actual source reread and paths checked. This is implementation-time AI review, not an independent blind trial. The publisher should arrange independent forward use if required.

## Model → output (deterministic tool checks)

Run `python3 -m unittest discover -s tests -v` from the skill root. Tests check real export invariants: native objects and references, HTML/drawio labels matching model text, source line ranges in supplied fixtures, escaping, Unicode/long labels, invalid references, and determinism. They do not prove arbitrary source analysis.

Open exported `index.html` in a browser. Check title/content; zoom +/−/reset/Fit width; scroll the viewport; open Source map and a detail link; switch pages back. Inspect long labels, decisions, side routes and bottom exits. Check console errors. On narrow screens, use zoom and scrolling; fit-width may yield very small text.

Open `diagram.drawio` in diagrams.net or another compatible editor when available. Check page tabs and internal links, select/move a node, edit a label and inspect connectors. Work on a copy. XML parse success proves structure only; if actual editor testing is unavailable, disclose that limitation.

Review HTML and drawio from the same saved model. Deliver the model alongside the two exports so corrections can regenerate both consistently. If one exported file is manually edited, its sibling is no longer guaranteed consistent.
