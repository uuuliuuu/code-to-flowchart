# code-to-flowchart

An Agent Skill for source-grounded execution flowcharts. AI reads pasted code, single files or a codebase and authors a traceable model; a Python standard-library script exports a self-contained zoomable HTML viewer and native editable drawio pages.

**This is not an automatic source parser.** The script renders an already-authored model. Source semantics, coverage and uncertainty require AI review.

## Use as a skill

Keep this folder intact (`SKILL.md` at its root) and add it to a host that loads Agent Skills. For a local Codex installation, copy the folder into the host's configured skills directory, normally `~/.codex/skills/code-to-flowchart`, then refresh the host's skill discovery. Installation is a user action; this package does not install itself. No remote publishing or account access is needed.

Example request:

> Use code-to-flowchart to explain the execution of this function. Follow available local callees, show early returns and failure paths, and give me HTML and editable drawio files. Use English labels.

The skill accepts pasted source without a project. **Diagram artifacts default to English**, including node/branch labels, titles, notes, source-map explanations and coverage descriptions, regardless of the conversation language. Another artifact language requires an explicit user request. Source identifiers and literal values are preserved when needed for accurate tracing; chat replies may follow the user's language. Large inputs are analyzed in explicit chunks with coverage tracking; see [analysis guidance](references/analysis.md).

**Prefer one readable diagram page.** Use same-page sections for phases and functions. Split only when a clear single-page layout is impractical or the user explicitly requests multiple views; multiple source files or functions do not automatically require multiple pages. Keep significant paths and readable text rather than squeezing everything into a tiny or excessively large canvas. The bundled multi-page examples demonstrate available detail navigation, not the default number of pages.

## Run the exporter directly

Requirement: Python 3.9+ standard library (tested with Python 3.13 on macOS). No pip packages or network service are required. From this folder:

```sh
python3 scripts/render.py examples/decision.json --out demo/decision
python3 scripts/render.py examples/retry.json --out demo/retry
python3 scripts/render.py examples/cross-file.json --out demo/cross-file
python3 -m unittest discover -s tests -v
```

Open `demo/retry/index.html` in a browser; use Diagram, +/−, Fit width and source-map detail buttons. Open `diagram.drawio` in diagrams.net for editing. Output also includes `model.json`. Re-running replaces these three filenames; use a dedicated output directory. Source files are not read or executed by the exporter.

Committed [examples/generated](examples/generated) contain ready-to-open outputs. The [model format](references/model.md) describes layout/evidence fields.

## Examples and evidence

| Source | Model | What it covers |
|---|---|---|
| `examples/source/decision.py` | `examples/decision.json` | English labels, decisions, early returns |
| `examples/source/retry.py` | `examples/retry.json` | Nested loops, continue/break, retry, exception/finally, unknown external calls; 3 pages |
| `examples/source/service.py` + `validation.py` | `examples/cross-file.json` | Local call/return, cross-file source map, external gateway boundary |

[Semantic review](examples/semantic-review.md) records source→model checks; tests separately cover model→export. See [verification](references/verification.md) before claiming an analysis is complete.

Tested environment: local Codex task on macOS, Python 3.13; generated HTML exercised in Chrome using Playwright. The retry drawio was opened in the real diagrams.net web editor: native node and edge labels were edited, and outer → attempts → body → attempts page links were followed. These edits were discarded; the packaged files remain generated from the models. Generic Agent Skill structure is used, but other hosts, operating systems, Python versions and source languages are not end-to-end certified. Concurrency, recursion and large-repository guidance is provided; no such behavior fixture has been run in v1.

## Limitations and optional PDF

The layout uses a manual row/column model and orthogonal routes, not automatic graph optimization. Complex graphs may need splitting and placement adjustments. Drawio retains native node/edge/label objects; editor layout can differ from HTML. Source references are traceability metadata, not proof of semantic correctness. Static assumptions and unread/external implementations remain visible in coverage.

PDF is not a default output. An optional route is diagrams.net's PDF export or a browser print workflow after arranging all desired pages. These require an editor/browser with PDF support and **have not been validated by this package**; the viewer hides inactive pages and uses a scroll viewport, so printing the HTML directly may omit content. Do not treat it as a verified multi-page PDF exporter.

## License

[MIT](LICENSE), code-to-flowchart contributors.
