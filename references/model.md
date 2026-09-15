# Graph model v1

UTF-8 JSON object:

- `version`: `1`; `title`: text.
- `coverage`: object with `read`, `unread`, `unknown` lists and a `status` string. Optional assumptions, chunks, call-site mappings or source hashes are displayed as JSON in the viewer.
- `diagrams`: nonempty list, each with unique text `id`, text `title`, optional text `notes`, `nodes`, `edges`, optional `groups`.
- Node: unique page-local text `id`, text `label`, nonnegative integer `row` and `col` (no shared cell), optional `kind` (default `process`), `source` list or nonempty `synthetic` explanation. Source entry: `{ "file": "relative/path.py", "start": 1, "end": 5 }`. `detail` optionally names an existing diagram id.
- Kinds: `start`, `end`, `process`, `decision`, `call`, `io`, `unknown`, `fork`, `join`. Kinds primarily supply visual cues; labels must explain operation semantics. Fork/join are colored blocks, not scheduling guarantees.
- Edge: page-local unique text `id`, `source`/`target` node ids, optional text `label`, optional `route`: `direct`, `left`, `right`. Every decision needs at least two labeled outgoing edges. Route upward edges explicitly to a side. Cross-page control transfers use linked nodes and labeled continuation mappings, not cross-page edges.
- Group: `{ "label": "Phase", "nodes": ["node-a", "node-b"] }`; all members must exist on the page. It draws an editable background section.

See `examples/decision.json` for a minimal complete model. Do not pass source files directly to the renderer. Source evidence is metadata, never loaded or executed by this script.

## Layout

Prefer a model with one diagram page when the complete flow remains readable. Use groups to distinguish phases or functions on that page. Rows determine vertical order; columns determine horizontal lanes. The exporter wraps Unicode node and edge text and expands row gaps for long edge labels. It uses orthogonal lines and outside lanes for side routes. Put side-exit nodes in another column; avoid direct edges skipping over intervening nodes in the same column. Keep groups compact and separate; long group titles and overlapping group ranges require manual inspection. Improve grouping, labels and routing before splitting. Use linked pages only when density, text size or connector ambiguity remains a problem, or the user asks for them; do not trade away logic or usable scale just to keep one page.

The layout is deterministic, not a general graph optimizer. It does not guarantee zero crossings/overlap for arbitrary graphs. Labels in drawio remain native editable edge values and may be placed differently by that editor. Check both formats visually when presentation matters. Source mapping lives in HTML's Source map and drawio node custom `source` attributes. Drawio page links use `data:page/id,<diagram-id>`.

## Data safety

Node labels, edge labels, notes, group names and source text are escaped for HTML/XML. The embedded JSON replaces angle brackets and ampersands before insertion into a script data block. Raw HTML labels are not supported. Source paths must be portable relative paths. The renderer checks structural references, not whether a cited file exists or a line actually supports the node; that is a separate semantic check.
