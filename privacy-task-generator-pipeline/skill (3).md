# OpenClaw Skill Map

*67 skills — analyzed from full SKILL.md reads. Each entry: Purpose, Tools Used, Capabilities, Requirements, Output.*

---

## Skill: academic-research

**Path:** `/usr/lib/node_modules/openclaw/skills/academic-research/SKILL.md`

### Purpose

Search 250M+ academic works via the OpenAlex API (free, no API key required) to conduct literature reviews, find papers by topic/author/DOI, explore citation chains, and fetch structured metadata (title, authors, abstract, citations, DOI, open access URL, source journal/venue). Includes a Python-based automated multi-step literature review workflow with thematic clustering and markdown output.

### Tools Used

- `exec` — Run Python scripts (`scholar-search.py`, `literature-review.py`) that make HTTP requests to the OpenAlex API

### Capabilities

- Search papers by keyword topic
- Search papers by author name
- Look up papers by DOI
- Get citation chain (forward + backward, both directions)
- Deep read: fetch abstract + full text for open access papers
- JSON output for programmatic use
- Automated literature review generation with configurable paper count, year range, and output format (markdown or JSON)
- Result caching in `/tmp/litreview_cache/` to avoid re-fetching

### Requirements

- `python3` (no external Python packages required — uses stdlib `urllib`)
- OpenAlex API (no key needed; openAlex.org)
- Scripts located at: `scripts/scholar-search.py`, `scripts/literature-review.py`
- `jq` recommended for pretty-printing JSON output

### Output

Structured paper data (title, year, authors up to 5, abstract, citation count, DOI, open access URL, source venue) written to stdout, a file (`--output`), or JSON (`--json`). Literature reviews are written as markdown files.

## Skill: agent-team-orchestration

**Path:** `/usr/lib/node_modules/openclaw/skills/agent-team-orchestration/SKILL.md`

### Purpose

Orchestrate multi-agent teams with defined roles, structured task lifecycles, explicit handoff protocols, and quality gates. Used when setting up teams of 2+ agents with different specializations, defining task routing, creating handoff protocols, establishing review workflows, and managing async communication between agents.

### Tools Used

- `sessions_spawn` — Spawn sub-agents with defined roles and output paths
- File-based task records — Task state tracked via files, a task board, or a database
- Reference files (team-setup.md, task-lifecycle.md, communication.md, patterns.md) read as needed

### Capabilities

- Define agent roles: Orchestrator, Builder, Reviewer, Ops
- Design task state lifecycle: `Inbox → Assigned → In Progress → Review → Done | Failed`
- Construct structured handoff messages (what was done, artifact paths, verification steps, known issues, next action)
- Cross-role review workflows (builders review specs, reviewers check builds, orchestrator reviews priorities)
- Spawn builder + reviewer pairs with predictable artifact directories
- Escalation and parallel research patterns
- Async communication setup between agents

### Requirements

- Reference files: `references/team-setup.md`, `references/task-lifecycle.md`, `references/communication.md`, `references/patterns.md`
- Clear artifact output paths must be specified when spawning agents
- Task state transitions owned by the Orchestrator (not self-updated by agents)
- High-reasoning model recommended for Orchestrator and Reviewer roles
- NOT for: single-agent setups, one-off task delegation, simple question routing

### Output

Artifacts produced by builder agents, tracked in task records, reported back through the Orchestrator to the user. Structured handoff messages at every state transition.

## Skill: api-dev

**Path:** `/usr/lib/node_modules/openclaw/skills/api-dev/SKILL.md`

### Purpose

Scaffold, test, document, and debug REST and GraphQL APIs from the command line. Covers the full API lifecycle: endpoint scaffolding, curl-based testing, OpenAPI spec generation and validation, mock servers, and HTTP debugging. Works on Linux, macOS, and Windows.

### Tools Used

- `exec` — Run curl commands, bash scripts, Python scripts, Node.js
- `write` / `edit` — Write API spec YAML files, server scaffolding scripts

### Capabilities

- HTTP testing with curl (GET, POST, PUT, PATCH, DELETE, OPTIONS for CORS)
- Verbose debugging, timing breakdowns, response header inspection
- Bash test runner (`assert_status`, `assert_json` style)
- Python test runner with `urllib.request`
- OpenAPI 3.0 spec scaffolding from existing endpoints
- OpenAPI spec validation via `npx @redocly/cli lint` and YAML validation
- Python mock server (`mock_server.py`) with configurable routes
- Node.js/Express REST API scaffolding with in-memory CRUD store
- JWT token decoding
- WebSocket testing via `npx wscat`
- Load/benchmark testing with loop + awk aggregation
- Port availability checking (`lsof`, `ss`)
- CORS preflight testing

### Requirements

- Required bins: `curl`, `node`, `python3`
- Optional bins: `jq` (JSON pretty-printing), `npx` (for @redocly/cli and wscat)
- Node.js for Express scaffolding
- `npm` for package installation
- Supported OS: linux, darwin, win32

### Output

- `curl` output (JSON, headers, timing) to stdout
- Test runner pass/fail counts and exit codes
- Scaffolded files (openapi.yaml, server.js, mock_server.py, api-test.sh)
- Exit code 0 on success, 1 on failure for test runners

## Skill: api-gateway

**Path:** `/usr/lib/node_modules/openclaw/skills/api-gateway/SKILL.md`

### Purpose

Managed API routing for 140+ third-party services via Maton (`https://api.maton.ai/`). Provides a unified authentication layer (single `MATON_API_KEY`) for connecting to external services (Slack, Notion, GitHub, Salesforce, Google Workspace, Stripe, HubSpot, etc.) without managing individual API keys. Handles OAuth flows, connection management, and error passthrough.

### Tools Used

- `exec` — Run Python and Node.js scripts that make HTTP requests to `https://api.maton.ai/`
- `browser` — Open OAuth authorization URLs (returned as part of connection creation response)

### Capabilities

- List/create/get/delete connections per app
- Route API calls through Maton proxy to 140+ services
- Multi-account support via `Maton-Connection` header
- Read-only operations (list, get) as default
- All modify operations (POST/PUT/PATCH/DELETE) require explicit user approval
- Connection status tracking (ACTIVE, PENDING, FAILED)
- Rate limit handling (10 req/sec per account + target API limits)
- Media upload URL handling (pre-signed URLs, use Python `urllib` to avoid shell corruption)
- Supported services include: Slack, GitHub, Notion, Salesforce, Stripe, Google (Gmail, Sheets, Drive, Calendar, etc.), HubSpot, Jira, Linear, Monday.com, Trello, Twilio, Zoom, Zoho CRM, and 100+ more

### Requirements

- `MATON_API_KEY` environment variable set via `export MATON_API_KEY="..."`
- Maton account at maton.ai
- Active connection established per service before use
- Network access to api.maton.ai
- Python `urllib` (stdlib) for all requests (avoid shell variable expansion with URLs containing `%` chars)
- Use `-g` flag with curl when URLs contain `[` or `]` characters
- For LinkedIn media uploads: must use Python `urllib`, not curl, due to encoded character handling

### Output

JSON responses from target APIs (pretty-printed via `json.dumps(..., indent=2)`) returned to stdout. Connection management returns structured JSON with connection_id, status, URL for OAuth completion, etc.

## Skill: automation-workflows

**Path:** `/usr/lib/node_modules/openclaw/skills/automation-workflows/SKILL.md`

### Purpose

Design and implement no-code automation workflows to save time and scale solo business operations. Covers opportunity identification (time-cost analysis), tool selection (Zapier vs Make vs n8n), workflow design (triggers, conditions, actions, error handling), building, testing, monitoring, and ROI calculation. Targeted at solopreneurs automating repetitive, rule-based, high-frequency tasks.

### Tools Used

- `exec` — Run any CLI commands needed for workflow setup
- `browser` — Configure tool accounts and OAuth connections in web dashboards
- `write` — Document workflows in Notion/Google Docs for maintenance
- `message` — Send error alert notifications to Slack/email

### Capabilities

- Automation audit: track tasks, calculate time cost, prioritize by ROI
- Tool selection guidance: Zapier (simple/cheap), Make (visual/complex), n8n (self-hosted/powerful)
- Workflow design template: trigger → conditions → actions → error handling
- Multi-step workflow implementation in chosen platform
- Testing: individual step verification, edge cases, failure injection
- Monitoring: weekly error log scans, monthly workflow audits
- Error handling setup: route failures to a central notification channel
- Advanced workflows: client onboarding, content distribution, customer health monitoring, invoice tracking
- ROI calculation formula to prioritize automation investments

### Requirements

- No code/CLI required — entirely no-code / platform UI
- Accounts for automation tools: Zapier, Make, or n8n
- Connected accounts for apps involved in workflows
- Clear understanding of the business process being automated
- NOT for: creative/judgment tasks, one-off tasks, processes requiring human nuance

### Output

Active automations running in chosen platform (Zapier Zaps, Make Scenarios, n8n workflows). Documented via Notion/Google Docs with: what it does, when it runs, apps connected, troubleshooting steps.

## Skill: backend-patterns

**Path:** `/usr/lib/node_modules/openclaw/skills/backend-patterns/SKILL.md`

### Purpose

Backend architecture patterns, API design principles, database optimization, caching strategies, error handling, authentication, rate limiting, background job queues, and structured logging for Node.js, Express, and Next.js API routes. Provides reusable TypeScript/JavaScript pattern implementations.

### Tools Used

- `exec` — Run npm/node commands, TypeScript compilation checks
- `write` / `edit` — Write pattern code files (repositories, services, middleware)
- `read` — Read existing codebase to apply patterns

### Capabilities

- RESTful API structure (resource-based URLs, query params for filtering/sort/pagination)
- Repository pattern: abstract data access with interface + implementation
- Service layer pattern: business logic separated from data access
- Middleware pattern: auth middleware wrapper for Next.js API routes
- Query optimization: select only needed columns, avoid N+1 via batch fetching
- Transaction pattern: atomic multi-table operations (e.g., Supabase RPC)
- Caching: Redis cache-aside pattern with TTL, cache invalidation
- Error handling: centralized ApiError class + error handler
- Retry with exponential backoff
- JWT token validation
- Role-based access control (RBAC) with permission matrix
- In-memory rate limiter
- Background job queue pattern (simple queue with processing flag)
- Structured JSON logging with requestId context

### Requirements

- Node.js / Express / Next.js (JavaScript/TypeScript)
- Supabase client for database operations
- Redis client for caching
- `jsonwebtoken` for JWT handling
- `zod` (optional) for validation
- No specific OS requirement

### Output

Pattern implementations (TypeScript/JavaScript) written to files in the user's project. These are copy-paste-ready patterns, not a standalone tool.

## Skill: cfo

**Path:** `/usr/lib/node_modules/openclaw/skills/cfo/SKILL.md`

### Purpose

Financial strategy and leadership: planning, cash management, fundraising, capital allocation, board reporting, risk management, M&A diligence. Splits into 4 domains via auxiliary files — `planning.md`, `cash.md`, `fundraising.md`, `operations.md`.

### Tools Used

- **read** — `planning.md`, `cash.md`, `fundraising.md`, `operations.md`
- **exec** — financial calculations (Python/shell)

### Capabilities

- **Financial planning:** 13-week rolling forecast, one-page models, scenario planning
- **Cash management:** runway visibility, burn rate tracking, cash flow forecasting
- **Fundraising:** timing strategy, term sheet evaluation, dilution modeling
- **Capital allocation:** ROI comparison across investments, opportunity cost analysis
- **Unit economics:** CAC/LTV/payback period, cohort analysis
- **Board reporting:** pre-board package, bad-news-early protocol
- **Company stage guidance:** pre-seed / seed / Series A / Series B+ priorities
- **Human escalation:** fundraising terms, layoffs, debt vs equity, M&A pricing, board comp, covenant negotiations

### Requirements

- No external API calls; no network required
- No persistent storage of confidential data

### Output

- Strategic guidance and recommendations (not autonomous execution)
- Spreadsheet models, forecasts, board-ready reports as text/markdown

## Skill: code

**Path:** `/usr/lib/node_modules/openclaw/skills/code/SKILL.md`

### Purpose

Coding workflow guidance providing planning, implementation, verification, and testing workflows for clean software development. Acts as a guidance layer — it does NOT autonomously execute code. User preferences (explicitly provided) are stored in `~/code/memory.md`. Serves as a decision-making framework for any coding task.

### Tools Used

- `read` — Read `~/code/memory.md`, reference files (`planning.md`, `execution.md`, `verification.md`, `state.md`, `criteria.md`)
- `write` — Write `~/code/memory.md` (only when user explicitly asks to store a preference)
- `exec` — Run code, tests, verification commands (only when user explicitly requests execution)
- `browser` — Open URLs related to the task (documentation, repos)

### Capabilities

- Check user preferences from `~/code/memory.md` before coding
- Plan before coding: break requests into independently testable steps
- Verify after each step: run tests after each function, screenshot after UI changes, full suite before delivery
- Store user preferences on explicit request only ("remember I prefer X" → add to memory.md)
- Sub-agent delegation (only with explicit user request)
- Multi-task state management via `state.md`
- User-defined acceptance criteria via `criteria.md`

### Requirements

- `~/code/` directory created on first use
- `~/code/memory.md` (created on first explicit user request to store a preference)
- Reference files: `planning.md`, `execution.md`, `verification.md`, `state.md`, `criteria.md`, `memory-template.md`
- User must explicitly control execution — this skill is guidance-only
- NO automatic network requests, NO autonomous code execution, NO modification of its own files

### Output

- Guidance and recommendations to the user (not autonomous execution)
- User preferences stored in `~/code/memory.md`
- All other data stays local to the user's project

## Skill: code-analysis

**Path:** `/usr/lib/node_modules/openclaw/skills/code-analysis-skills/SKILL.md`

### Purpose

Analyze Git repositories to evaluate developer behavior: commit habits, work patterns, development efficiency, code style, code quality, and slacking index. Produces structured reports (Markdown, JSON, HTML, PDF) with scores, grades, strengths, weaknesses, and actionable suggestions for each developer. Supports multi-developer comparison, team leaderboards, and date range filtering.

### Tools Used

- `exec` — Run Python analysis scripts (`src/main.py`, analyzer modules, reporter modules) with CLI arguments

### Capabilities

- Single or batch Git repository scanning (recursive `--scan-all`)
- Per-author filtering and comparison (Alice vs Bob)
- Date range filtering (`--since`, `--until`)
- Branch-specific analysis
- Seven analysis dimensions: Developer Evaluation (score/grade), Slacking Index, Commit Habits, Work Habits, Development Efficiency, Code Style, Code Quality
- Output formats: markdown, json, html, pdf (or comma-separated multi-format)
- Privacy/slacking index scoring (Workaholic → Slacking Master scale)
- Six-dimension scoring: Commit Discipline (15%), Work Consistency (15%), Efficiency (20%), Code Quality (25%), Code Style (10%), Engagement (15%)
- Grades: S (90-100) through F (0-34)
- Bus Factor, code churn rate, rework rate, conventional commits compliance

### Requirements

- Python packages: `gitpython`, `pydriller`, `radon`, `tabulate`, `jinja2`, `click`, `reportlab`
- Optional (for PDF): `weasyprint` (preferred) or `pdfkit` (requires system wkhtmltopdf)
- `python3` with the skill's `src/` module accessible
- Required parameter: `--repo-path` (or `-r`)
- Directory scanning max depth: 5 levels
- Author matching supports fuzzy matching on name or email
- Informed consent required before analyzing team repositories
- Results must not be used directly for performance reviews or punitive decisions

### Output

Structured reports in chosen format (markdown/json/html/pdf) written to stdout or an output file. Reports include: overall score, grade, dimension scores, strengths, weaknesses, suggestions, slacking index interpretation, cross-developer comparison tables, and leaderboards.

## Skill: data-analysis

**Path:** `/usr/lib/node_modules/openclaw/skills/data-analysis/SKILL.md`

### Purpose

Data analysis and visualization for SQL, spreadsheets, notebooks, dashboards, and ad hoc tables. Supports KPI debugging, experiment readouts, funnel/cohort analysis, anomaly reviews, executive reporting, and quality checks. Prefers analytical judgment over mechanical computation — every analysis must connect to a decision. Methodologically rigorous with statistical checks and uncertainty quantification.

### Tools Used

- `exec` — Run SQL queries, Python/R scripts, notebook execution
- `read` — Read reference files (`metric-contracts.md`, `chart-selection.md`, `decision-briefs.md`, `pitfalls.md`, `techniques.md`)
- `write` — Write analysis outputs, reports, decision briefs

### Capabilities

- Metric contract definition: entity, grain, numerator, denominator, time window, timezone, filters, exclusions, source of truth
- Statistical rigor checklist: sample size, comparison group fairness, multiple comparison correction, effect size, confidence intervals
- Chart selection by analytical question: trend, comparison, distribution, relationship, composition, funnel, cohort retention
- Hypothesis testing (p-value, effect size, CI)
- Regression/correlation analysis
- Cohort analysis (retention curves by cohort)
- Segmentation (profiles + statistical comparison)
- Anomaly detection
- Decision brief output format: answer, evidence, confidence, caveats, next action
- Stress-test claims: segment by confounders, compare right baseline, quantify uncertainty
- Red flag escalation: predetermined conclusions, small samples, data quality issues, uncontrolled confounders

### Requirements

- Reference files: `metric-contracts.md`, `chart-selection.md`, `decision-briefs.md`, `pitfalls.md`, `techniques.md`
- No local folder requirements, no persistent memory, no setup state
- No external network requests (all data stays local)
- No credentials stored
- Related skills: `sql`, `csv`, `dashboard`, `report`, `business-intelligence` (installable via clawhub)

### Output

Analysis written to stdout or a file. Every output includes: the insight (not methodology), uncertainty ranges (not point estimates), limitations, and recommended next steps. Decision briefs are structured for stakeholders with business implications translated from technical details.

## Skill: devops

**Path:** `/usr/lib/node_modules/openclaw/skills/devops/SKILL.md`

### Purpose

Automate deployments, manage infrastructure, and build reliable CI/CD pipelines. Covers CI/CD best practices, deployment strategies (blue-green, canary, rolling), Infrastructure as Code (Terraform, Ansible, CloudFormation), container best practices, secrets management, monitoring/alerting, reliability engineering (SLOs, error budgets, chaos engineering), and networking principles.

### Tools Used

- `exec` — Run CLI tools for Terraform, Ansible, Docker, CI pipeline diagnostics
- `write` / `edit` — Write IaC config files, CI pipeline configs, runbooks
- `read` — Review existing configs, plan/apply diffs

### Capabilities

- CI/CD pipeline design: fail-fast linting, dependency caching, pinned action SHA versions, parallel jobs, secret masking
- Deployment strategies: blue-green (atomic traffic switch), canary (% routing), rolling (incremental)
- Infrastructure as Code: Terraform plan/apply workflow, remote state management, module patterns, workspace/environment separation
- Container best practices: one process per container, non-root users, health checks mandatory, immutable images
- Secrets management: vault, sealed secrets, CI secret storage, rotation automation, per-environment secrets, audit logging
- Monitoring: four golden signals (latency, traffic, errors, saturation), symptom-based alerting, actionable alerts only, structured JSON logs
- Reliability: SLO definition, error budgets, chaos engineering in staging, runbooks for incidents, blameless post-mortems
- Networking: private subnets, TLS everywhere (zero trust), DNS service discovery, load balancer health checks, default-deny firewalls

### Requirements

- No specific bins listed, but typically: `terraform`, `ansible`, `docker`, `kubectl`, CI CLI tools
- CI/CD platform (GitHub Actions, GitLab CI, etc.)
- Container runtime (Docker/Podman)
- Supported OS: linux, darwin, win32

### Output

Infrastructure and pipeline configuration files written to the project. Operational guidance (runbooks, post-mortem templates) written as docs. No standalone output — this is a pattern/best-practice skill.

## Skill: docker-essentials

**Path:** `/usr/lib/node_modules/openclaw/skills/docker-essentials/SKILL.md`

### Purpose

Essential Docker commands and workflows for container management, image operations, networking, volumes, and debugging. Provides a comprehensive quick reference covering container lifecycle, inspection, image building and management, Docker Compose, networking, volumes, system cleanup, and common development workflows (dev containers, database containers, multi-stage builds).

### Tools Used

- `exec` — Run `docker` and `docker-compose` CLI commands

### Capabilities

- Container lifecycle: run (detached, named, port-mapped, env-var, volume-mounted, auto-remove, interactive), stop, start, restart, rm, prune
- Container inspection: logs (`-f`, `--tail`, `-t`), exec (command, interactive shell, as specific user), inspect (JSON path extraction), stats, top
- Image building: build from Dockerfile, custom Dockerfile path, build args, no-cache
- Image management: list, pull, tag, push, rmi, prune
- Docker Compose: up, down (`-v`), logs (`-f` per service), ps, exec, restart, build, scale
- Networking: list, create, connect/disconnect container, inspect, rm
- Volumes: list, create, inspect, rm, prune, run with volume
- System: disk usage (`docker system df`), prune (all, images, volumes), info, version
- Common workflows: dev container with volume mount, database container (Postgres), shell into running container, file copy in/out of container
- Multi-stage Dockerfile builds

### Requirements

- Required binary: `docker` (CLI)
- Optional: `docker-compose` (or `docker compose` v2+)
- Optional: `jq` (for JSON path processing in inspect output)
- Official docs: [https://docs.docker.com/](https://docs.docker.com/)
- Dockerfile reference: [https://docs.docker.com/engine/reference/builder/](https://docs.docker.com/engine/reference/builder/)
- Compose file reference: [https://docs.docker.com/compose/compose-file/](https://docs.docker.com/compose/compose-file/)

### Output

Docker commands return CLI output to stdout (container logs, inspect JSON, stats tables, ps listings). No files written unless explicitly using `docker cp`.

*End of Batch 1 — 11 skills documented.*

## Skill: desktop-control

**Path:** `/usr/lib/node_modules/openclaw/skills/desktop-control/SKILL.md`

### Purpose

Advanced desktop automation — pixel-perfect mouse control, keyboard input, screen capture, window management, clipboard. Wraps PyAutoGUI, Pillow, OpenCV, PyGetWindow.

### Tools Used

- **exec** — Python snippets (pyautogui, pygetwindow)
- **read** — source code
- **write** — scripts + screenshots

### Capabilities

- Mouse: absolute/relative, clicks (left/right/middle/double/triple), drag & drop, scroll, position tracking
- Keyboard: typing (configurable WPM), hotkey combos, special keys, key hold/release
- Screen: full/region screenshots (PIL), pixel color, OpenCV template finding (find_on_screen), multi-monitor
- Window: list, activate by title, get active window
- Clipboard: copy/get text
- Safety: failsafe, pause, approval mode, bounds checking

### Requirements

- `pyautogui`, `pillow`, `opencv-python`, `pygetwindow` (pip)
- Linux/macOS/Windows

### Output

- Actions execute silently; `screenshot()` → PIL Image; `find_on_screen()` → `(x,y,w,h)` or `None`; `get_mouse_position()` → tuple; clipboard → `str`

## Skill: edge-tts

**Path:** `/usr/lib/node_modules/openclaw/skills/edge-tts/SKILL.md`

### Purpose

Microsoft Edge neural TTS. Supports voices/languages, rate/pitch/volume, multiple output formats, subtitle generation.

### Tools Used

- **tts** (built-in) — returns `MEDIA:` audio path
- **exec** — runs `node tts-converter.js`, `node config-manager.js`
- **read** — docs

### Capabilities

- MP3 generation from text
- Dozens of neural voices across many languages
- Rate/pitch/volume adjustment
- Output format/quality selection
- Word-level subtitle JSON generation
- Voice listing
- Preferences persistence (`~/.tts-config.json`)
- Proxy support (`--proxy`)
- Automatic TTS keyword filtering
- Temp files: `/tmp/edge-tts-temp/`

### Requirements

- `node-edge-tts` + `commander` npm packages
- Internet (Microsoft Edge online TTS, no API key)

### Output

- `tts` tool → `MEDIA: /path/to/audio.mp3`; `tts-converter.js --output`; `--list-voices` → stdout; `config-manager.js` → JSON stdout

## Skill: excalidraw

**Path:** `/usr/lib/node_modules/openclaw/skills/excalidraw/SKILL.md`

### Purpose

Generate hand-drawn style PNG diagrams (flowcharts, architecture diagrams) from Excalidraw JSON using a Node.js render script.

### Tools Used

- **write** — Excalidraw JSON to `/tmp/`
- **exec** — `node render.js input.excalidraw output.png`
- **read** — SKILL.md, render script
- **canvas** — present PNG

### Capabilities

- Elements: rectangle, ellipse, diamond, arrow, line, text
- Styling: stroke color, fill (hachure/cross-hatch/solid), stroke width, roughness (0=clean-2=sketchy)
- Arrow binding: from/to auto-calculates edge intersections; absolutePoints for waypoints
- Arrow labels: text near midpoint
- Font families: 1=hand-drawn, 2=sans-serif, 3=monospace
- Layout guidance: nodes 140-200x50-70px, diamonds 180-200x100-120px, spacing 60-120px

### Requirements

- Node.js
- `render.js` at `<skill_dir>/scripts/render.js`
- No credentials

### Output

- PNG at specified output path via `exec`; delivered via `canvas` or `message`

## Skill: excel-xlsx

**Path:** `/usr/lib/node_modules/openclaw/skills/excel-xlsx/SKILL.md`

### Purpose

Create, inspect, edit Excel workbooks (.xlsx/.xlsm/.xls/.csv/.tsv) — formula reliability, date correctness, type preservation, formatting, structure.

### Tools Used

- **exec** — Python/openpyxl/pandas scripts
- **write** — Python scripts, CSV/TSV intermediates
- **read** — existing workbook inspection

### Capabilities

- Read: sheets, values, formulas, styles, merged cells, comments, named ranges, hidden rows/cols
- Write: formulas (not hardcoded), proper references, styling
- Formula verification: no #REF!/#DIV/0!/#VALUE!/#NAME?
- Date handling: 1900 vs 1904 systems
- Type preservation: long IDs, leading zeros, 15-digit truncation prevention
- Structure preservation: sheet order, merged ranges, hidden sheets, conditional formatting, filters, data validation, freeze panes
- Template conventions
- Large file handling: streaming, dtype spec, sheet targeting

### Requirements

- `openpyxl`, `pandas` (pip)
- No API keys; local files only

### Output

- `.xlsx` file saved to disk; summary of changes as text

## Skill: ffmpeg-video-editor

**Path:** `/usr/lib/node_modules/openclaw/skills/ffmpeg-video-editor/SKILL.md`

### Purpose

Translate natural language video editing into FFmpeg commands. No API calls — pure local CLI.

### Tools Used

- **exec** — runs ffmpeg commands
- **write** — intermediate files (files.txt for concat, SRT)

### Capabilities

- Cut/Trim (-ss/-to, -c copy)
- Format conversion (mp4, mkv, avi, webm, mov, flv, wmv)
- Aspect ratio letterboxing (16:9, 4:3, 1:1, 9:16, 21:9)
- Resolution resize (4K, 1080p, 720p, 480p, 360p)
- CRF compression (18=high, 23=balanced, 28=small)
- Audio extraction (mp3, aac, wav, flac, ogg)
- Audio removal (-an)
- Speed change (setpts + atempo, 0.5x-2x)
- GIF creation (fps, lanczos, loop)
- Rotate/flip (transpose, hflip, vflip)
- Frame extraction (single frame as JPEG)
- Watermark overlay
- Subtitle burning (SRT)
- Concatenation (files.txt + ffmpeg -f concat)

### Requirements

- `ffmpeg` + `ffprobe` in PATH
- Local files only

### Output

- FFmpeg command with `-y -hide_banner`; auto-generated output filename

## Skill: flight-search

**Path:** `/usr/lib/node_modules/openclaw/skills/flight-search/SKILL.md`

### Purpose

CLI flight search via Google Flights — no API key required. Built on `fast-flights` Python library.

### Tools Used

- **exec** — `uvx flight-search ...` or `flight-search ...`

### Capabilities

- One-way / round-trip search (airport codes + dates)
- Passenger count (--adults, --children)
- Seat class filter (economy, premium-economy, business, first)
- Result limit (default 10)
- Output: text (ASCII table) or json

### Requirements

- `uvx` (from `uv` package manager) or `uv tool install flight-search`
- Internet (scrapes Google Flights, no API key)

### Output

- Human: ASCII table with airline, times, duration, stops, price, BEST marker
- JSON: structured with origin, destination, date, current_price, flights[]

## Skill: frontend-design-3

**Path:** `/usr/lib/node_modules/openclaw/skills/frontend-design-3/SKILL.md`

### Purpose

Production-grade frontend (HTML/CSS/JS, React, Vue) with distinctive aesthetics that avoid AI slop. Bold design direction across typography, color, motion, spatial composition.

### Tools Used

- **write** — component/source files
- **exec** — dev servers, build commands
- **read** — existing code
- **canvas** — present output

### Capabilities

- Design thinking: brutalist / retro-futuristic / luxury / maximalist / organic direction
- Typography: distinctive fonts only; forbids Arial, Inter, Roboto
- Color: CSS variables, dominant+accent; forbids purple-on-white gradients
- Motion: CSS-only where possible; Motion library for React
- Spatial: asymmetry, overlap, diagonal flow, grid-breaking, negative space
- Backgrounds: gradient meshes, noise textures, geometric patterns, shadows, grain
- Anti-patterns: forbids Space Grotesk, cliched color schemes
- Light + dark themes
- Complexity matches vision (maximalist → elaborate, minimalist → restrained)

### Requirements

- No API/credentials — pure frontend
- Node.js/npm for React/Vue dev servers

### Output

- Working code → workspace; presented via `canvas`

## Skill: gh-issues

**Path:** `/usr/lib/node_modules/openclaw/skills/gh-issues/SKILL.md`

### Purpose

Automatic GitHub issue fixing — fetch, present, spawn sub-agents to fix, open PRs, monitor reviews. 6-phase pipeline.

### Tools Used

- **exec** — git, curl (GitHub REST API), jq, file I/O
- **sessions_spawn** — parallel sub-agents (up to 8)
- **write** — claims file, cursor file, files.txt
- **read** — claims/cursor, source code
- **message** — Telegram notifications
- **process** — watch loops

### Capabilities

- Phase 1: Parse owner/repo + flags (--label, --limit, --milestone, --assignee, --state, --fork, --watch, --dry-run, --yes, --reviews-only, --cron, --notify-channel)
- Phase 2: Fetch via GitHub REST API; milestone resolution; @me resolution; filter PRs
- Phase 3: Present markdown table; fork-mode; dry-run; yes-mode; confirmation prompt
- Phase 4: Pre-flight checks (dirty tree, base branch, git remote, GH_TOKEN, existing PR, claim tracking)
- Phase 5: Spawn sub-agents → branch → fix → test → commit → push → PR; cron = sequential; normal = up to 8 parallel
- Phase 6: PR review — fetch reviews/comments; filter bot comments; spawn fix sub-agents; reply to threads
- Watch mode: polls, filters processed, runs Phase 6 each cycle

### Requirements

- `GH_TOKEN` env var (injected by OpenClaw)
- `git`, `curl`, `jq`
- `/data/.clawdbot/` writable
- NOT `gh` CLI — raw curl only
- Optional: Telegram channel ID for --notify-channel

### Output

- Summary table: issue#, title, status (PR opened/Failed/Timed out/Skipped), PR URL, notes
- Final: `Processed {N} issues: {success} PRs opened, {failed} failed, {skipped} skipped.`
- Telegram notification with PR links

## Skill: github

**Path:** `/usr/lib/node_modules/openclaw/skills/github/SKILL.md`

### Purpose

Wrapper for official `gh` CLI. Quick reference for PRs, issues, CI/workflows, API queries.

### Tools Used

- **exec** — `gh` CLI commands
- **read** — SKILL.md reference

### Capabilities

- PR: list, view, create, merge (squash/merge/rebase), check CI
- Issues: list, create, close
- CI/Workflows: list runs, view details, failed step logs, re-run failed jobs
- API: `gh api` with `--jq` for any repo data
- JSON: `--json` flag + `--jq` field extraction
- Auth: `gh auth login/status`; handles `GH_CONFIG_DIR`

### Requirements

- `gh` CLI (brew/apt)
- `gh auth login`
- `GH_CONFIG_DIR` if gateway home differs from operator home
- Network to github.com

### Output

- Text or JSON output; `gh` handles auth internally

## Skill: gog

**Path:** `/usr/lib/node_modules/openclaw/skills/gog/SKILL.md`

### Purpose

Google Workspace CLI — Gmail, Calendar, Drive, Contacts, Sheets, Docs. OAuth setup required.

### Tools Used

- **exec** — `gog <service> <command>` CLI
- **write** — body files (--body-file), Sheets data files
- **read** — exported Docs content

### Capabilities

- **Gmail:** search threads/messages, send plain/HTML/reply, drafts
- **Calendar:** list events, create (summary/time/color), update
- **Drive:** full-text file search
- **Contacts:** list contacts
- **Sheets:** get/update/append/clear cell ranges as JSON, metadata
- **Docs:** export plain text, cat content

### Requirements

- `gog` binary (Homebrew: `brew install steipete/tap/gogcli`)
- OAuth: `gog auth credentials ...` then `gog auth add ... --services ...`
- `GOG_ACCOUNT` env var (optional)
- Network to Google APIs

### Output

- Human-readable default; `--json` for scripting; Sheets → JSON; Docs → plain text

## Skill: goplaces

**Path:** `/usr/lib/node_modules/openclaw/skills/goplaces/SKILL.md`

### Purpose

Google Places API (New) CLI — text search, place details, geocoding, reviews. Human-readable or `--json`.

### Tools Used

- **exec** — `goplaces <command>` CLI
- **read** — SKILL.md reference

### Capabilities

- Text search: `goplaces search "coffee" --open-now --min-rating 4 --limit 5`
- Location bias: `--lat/--lng/--radius-m`
- Pagination: `--page-token`
- Geocoding resolve: `goplaces resolve "Soho, London" --limit 5`
- Place details: `goplaces details <place_id> --reviews`
- `--json` for scripting
- `--no-color` / `NO_COLOR` env var

### Requirements

- `goplaces` (Homebrew: `brew install steipete/tap/goplaces`)
- `GOOGLE_PLACES_API_KEY` env var
- Network to Google Places API

### Output

- Human: names, addresses, ratings, price level, open status
- JSON: structured for scripting

## Skill: browser-automation

**Path:** `~/.openclaw/plugin-skills/browser-automation/SKILL.md`

### Purpose

Guides the agent in using the `browser` tool for multi-step web automation flows — including login checks, tab management, stale-ref recovery, and Google Meet sessions. It is a living workflow handbook for reliable browser control.

### Tools Used

- `**browser`** — OpenClaw's primary browser-automation tool (snapshot, act, tabs, open, navigate, screenshot, etc.)
- `**exec*`* — Used indirectly to run CLI commands such as `openclaw browser doctor`

### Capabilities

- **Pre-action state checks** — Verifies browser availability, profiles, and open tabs before taking any action
- **Stable tab management** — Opens labeled tabs, reuses existing ones, closes duplicates via `tabId`; never passes raw numeric positions as `targetId`
- **Snapshot-before-click discipline** — Always runs `snapshot` on the intended `targetId` before acting; uses `refs="aria"` for durable Playwright-style refs
- **Stale-ref recovery** — Re-snapshots the same `targetId` after a failure, finds the current visible control, retries once with the new ref
- **User browser attachment** — Uses `profile="user"` to attach to the user's existing Chromium session (cookies/login matter) when needed; omits `timeoutMs` on certain actions that the driver rejects per-call overrides for
- **Google Meet integration** — Handles camera/mic permission screens as progress states (not login failures), manages one labeled tab per meeting, supports retry loops
- **Obstruction reporting** — Reports exactly what manual action is needed (login, 2FA, captcha, permission approval) rather than looping or misdiagnosing

### Requirements

- Chromium-based browser (v144+) running on the selected host/node
- OpenClaw browser control server must be active
- `openclaw browser doctor` available for diagnostic use
- For `profile="user"`: the user's browser must be running with existing session/profile

### Output

- Text instructions embedded in the skill guide itself (no structured output file)
- The agent receives guidance on workflow decisions; actions and results are returned directly to the calling agent or user

## Skill: hatch-trust

**Path:** `~/.openclaw/plugin-skills/hatch-trust/SKILL.md`

### Purpose

Teaches the agent the data classification and tool-tier system used by the `hatch-trust` plugin, which enforces runtime approval prompts when sensitive data crosses tool boundaries. The skill is **always active** (always-on plugin). The agent's job is to **attempt** the user's requested operation — the plugin halts it at the boundary for user approval rather than refusing preemptively.

### Tools Used

- (No direct tool calls) — This is a policy/behavioral skill that governs how other tool calls are structured and whether they proceed

### Capabilities

- **Tier-aware tool selection** — When multiple tools satisfy a goal, prefers the lowest-tier capable tool (Tier 1 local > Tier 2 first-party cloud > Tier 3 third-party API)
- **Sensitivity-aware summarization** — After any turn involving L3/L4 data, paraphrases values by role rather than echoing them (e.g., "the user's medical record number" not the actual MRN)
- **Policy bypass behavior** — If the user explicitly asks for an operation that the plugin might block, the agent emits the tool call anyway; the block message is informational and tells the user how to bypass
- **Unknown-tool handling** — Unknown tools fail closed (treated as Tier 3 with L1 max by default)

### Requirements

- The `hatch-trust` plugin must be installed and active in the workspace
- Tool-levels configuration at `<workspaceDir>/.openclaw/hatch-trust/tool-levels.json` controls per-tool maximum allowed data levels
- User must be present to respond to approval prompts (allow-once / allow-always / deny)

### Output

- The plugin halts the tool call and presents an approval prompt to the user at runtime
- No structured output file — the skill itself describes the classification system, tool tiers, bypass mechanisms, and what the plugin does per call

## Skill: health

**Path:** `/usr/lib/node_modules/openclaw/skills/health/SKILL.md`

### Purpose

Provides personalized wellness guidance while maintaining strict safety boundaries. Designed for general health, nutrition, sleep, fitness, and lifestyle advice. Explicitly does **not** diagnose, treat, or prescribe.

### Tools Used

- (No direct tool calls) — This is a guidance/behavioral skill

### Capabilities

- **Safety boundary enforcement** — Never diagnoses, treats, or prescribes; always recommends consulting healthcare providers for medical concerns
- **Evidence-level distinction** — Distinguishes research-backed findings from emerging data and theoretical mechanisms
- **Personal baseline learning** — Learns individual norms over 2–4 weeks before making recommendations; accounts for medications, conditions, schedule, stress, sleep patterns
- **Correlation pattern tracking** — Tracks how sleep quality affects food choices, exercise impact on mood, etc.
- **8th-grade reading level** — Uses plain language; avoids medical jargon that confuses
- **Specific actionable guidance** — "Drink 16oz water when you wake up" not "stay hydrated"
- **Timeline expectations** — Includes expected timeframes for improvement
- **One-behavior-change-at-a-time** — Starts with minimal effective dose (e.g., 5-minute walk over ambitious gym plans)
- **Progress tracking** — Celebrates consistency over perfection; tracks energy, mood, sleep quality, not just weight/steps; weekly/monthly trends over daily snapshots

### Requirements

- No bins, no env vars, no OS requirements — purely advisory
- Agent should be in an active conversation with the user to build personal baselines over time

### Output

- Plain conversational guidance returned directly in the chat context
- No structured data files; this skill is entirely about how the agent communicates about wellness topics

## Skill: healthcheck

**Path:** `/usr/lib/node_modules/openclaw/skills/healthcheck/SKILL.md`

### Purpose

Audits and hardens hosts running OpenClaw for SSH, firewall, updates, exposure, cron checks, and risk posture. Produces a staged remediation plan that preserves remote access while tightening security. Requires explicit approval before any state-changing action.

### Tools Used

- `**exec`** — Runs read-only OS commands (`uname -a`, `ss -ltnup`, `ufw status`, `tmutil status`, etc.) and OpenClaw CLI commands
- `**openclaw security audit [--deep] [--fix] [--json]`** — OpenClaw's built-in security audit tool
- `**openclaw update status**` — Checks current channel and update availability
- `**openclaw cron add|list|runs|run**` — Schedules periodic audits (Gateway scheduler)
- `**memory_***` tools — Conditionally writes audit summaries to `memory/YYYY-MM-DD.md` and `MEMORY.md` when the user opts in and the session is a private/local workspace

### Capabilities

- **Model self-check** — Detects if the current model is below state-of-the-art (Opus 4.5, GPT 5.2+) and recommends switching without blocking execution
- **System context establishment** — Reads OS type, privilege level, access path, network exposure, backup status, disk encryption, auto-update status from the environment before asking the user
- **OpenClaw security audit** — Runs `openclaw security audit` (fast) and optionally `--deep`; offers `--fix` to apply safe defaults (tightens OpenClaw config and file permissions only)
- **Update status check** — Reports current channel and available updates
- **Risk tolerance determination** — Profiles: Home/Workstation Balanced, VPS Hardened, Developer Convenience, or Custom
- **Staged remediation plan** — Shows plan before any changes: target profile, gaps, step-by-step commands, rollback plan, access-preservation strategy, risks, credential hygiene notes
- **Guided execution with confirmations** — Shows exact command, explains impact/rollback, confirms access will remain, stops on unexpected output
- **Verification report** — Re-checks firewall, ports, remote access, re-runs OpenClaw audit; delivers final posture report
- **Periodic scheduling** — Offers to schedule `healthcheck:security-audit` and `healthcheck:update-status` via `openclaw cron add`; matches existing jobs by exact name before creating/editing
- **Memory writes (conditional)** — Appends dated summaries to `memory/YYYY-MM-DD.md` and `MEMORY.md` only when user opts in and session is private/local; redacts secrets

### Requirements

- OpenClaw CLI (`openclaw`) must be available in PATH
- `openclaw security audit`, `openclaw update status`, `openclaw cron` subcommands must be supported in the installed version
- Agent should be running with sufficient permissions to execute read-only diagnostic commands
- User must be available to approve state-changing actions (firewall rules, SSH changes, packages, etc.)
- `gateway.nodes.allowCommands` must include `dir.fetch` if memory writes are used

### Output

- Interactive numbered choices presented to the user at each decision point
- Final posture report delivered as formatted text
- Optional `memory/YYYY-MM-DD.md` appends (if opted in)
- Cron jobs created/edited via OpenClaw scheduler

## Skill: humanizer

**Path:** `/usr/lib/node_modules/openclaw/skills/humanizer/SKILL.md`

### Purpose

Removes signs of AI-generated writing from text to make it sound more natural and human. Based on Wikipedia's "Signs of AI writing" guide maintained by WikiProject AI Cleanup. Detects and fixes 24 distinct AI-writing patterns across content, language/grammar, style, communication, filler/hedging, and conclusion categories.

### Tools Used

- `**read`** — Reads input text before processing
- `**write`** — Writes the humanized output text
- `**edit**` — Makes targeted rewrites to specific problematic sections
- `**exec**` — Used via `grep` (referenced in allowed-tools but not in core workflow)

### Capabilities

- **24 AI-pattern categories detected and fixed:**
  - Content: inflated significance/legacy language, media coverage/notability claims, superficial -ing analyses, promotional language, vague attributions/weasel words, outline-like "Challenges and Future Prospects" sections
  - Language/Grammar: overused AI vocabulary (Additionally, crucial, pivotal, showcase, etc.), copula avoidance (serves as, stands as, boasts), negative parallelisms (Not only...but), rule of three overuse, elegant variation (synonym cycling), false ranges
  - Style: em dash overuse, boldface overuse, inline-header vertical lists, title case in headings, emoji decoration, curly quotation marks
  - Communication: collaborative artifact language (I hope this helps, Let me know), knowledge-cutoff disclaimers (as of [date]), sycophantic/servile tone
  - Filler/Hedging: filler phrases (In order to, Due to the fact that), excessive hedging, generic positive conclusions
- **Personality injection** — Goes beyond pattern removal; injects actual human voice: opinions, varied rhythm, first-person perspective, acknowledged complexity, specific feelings
- **Soulless-writing detection** — Identifies voiceless but "clean" text (same sentence length, no opinions, no humor, reads like Wikipedia)
- **Full rewrite workflow** — Reads input → identifies patterns → rewrites each section → ensures natural flow, varied structure, specific details, appropriate tone

### Requirements

- No bins, no env vars, no special OS requirements
- Allowed tools: Read, Write, Edit, Grep, Glob, AskUserQuestion
- Works on any text content passed to the skill

### Output

- The rewritten humanized text (as direct output)
- Optional brief summary of changes made
- Based on Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup) reference

## Skill: language-learning

**Path:** `/usr/lib/node_modules/openclaw/skills/language-learning/SKILL.md`

### Purpose

AI language tutor for learning ANY language through conversation, vocabulary drills, grammar lessons, flashcards, immersive practice, script/writing system instruction, cultural context, and exam preparation. Supports all human languages across three tier levels with full curriculum (Tier 1) through basic phrase tutoring (Tier 3).

### Tools Used

- (No direct tool calls) — Pure conversation and content-generation skill; all teaching is delivered as text output in the chat context

### Capabilities

- **Vocabulary Builder** — Thematic word groups with transliteration, example sentences, translations, memory hooks; quiz formats (target→English, English→target, fill-in-blank, audio-style)
- **Grammar Lessons** — Pattern-recognition method (3-4 examples → user identifies rule → explanation → practice sentences → correction with encouragement)
- **Conversation Practice** — Simulated real conversations at user's level; set scene → start in target language → user responds → gentle corrections → recap with corrections, new vocab, cultural notes
- **Flashcard Drill** — Spaced-repetition rounds (10 new → quiz all → re-quiz missed + 5 new → full review); supports word/translation, sentence completion, conjugation tables, character/script recognition
- **Script & Writing System Instruction** — Systematic learning for Japanese (Hiragana→Katakana→Kanji), Chinese (Pinyin→characters), Korean (Hangul), Arabic, Hindi/Bangla, Russian, Thai, Greek
- **Cultural Context** — Politeness levels, gestures, taboos, humor, idioms/proverbs, food vocabulary, celebrations
- **Exam Preparation** — DELE, JLPT, HSK, DELF, TOPIK, Goethe-Zertifikat, and 15+ other certification exams with timed drills and scoring rubrics
- **7 teaching modes** with 4 proficiency levels (Absolute beginner → Advanced) and 4 learning goals (Travel, Conversation, Professional, Academic, Cultural, Heritage, Just for fun)
- **Adaptive teaching** — Tracks struggling words/concepts, revisits difficult material, gradually increases complexity

### Requirements

- No bins, no env vars — purely conversational
- Works best in active chat sessions where the user can respond in the target language

### Output

- Vocabulary entries with transliteration and translation
- Grammar explanations with examples and practice sentences
- Conversation transcripts with corrections and cultural notes
- Flashcard rounds with quiz/answer format
- Session recaps with progress tracking and homework assignments

## Skill: markdown-converter

**Path:** `/usr/lib/node_modules/openclaw/skills/markdown-converter/SKILL.md`

### Purpose

Converts documents and files to Markdown format using `uvx markitdown` — no installation required. Supports a broad range of formats including PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, images (with EXIF/OCR), audio (with transcription), ZIP archives, YouTube URLs, and EPub. Used to make structured files readable by LLMs or for text analysis.

### Tools Used

- `**exec`** — Runs `uvx markitdown` as a shell command with file paths or stdin; handles output redirection to files

### Capabilities

- **Document conversion** — PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx, .xls)
- **Web/data format conversion** — HTML, CSV, JSON, XML
- **Media conversion** — Images (EXIF metadata + OCR text extraction), Audio (EXIF + transcription)
- **Other formats** — ZIP (iterates contents), YouTube URLs (transcription), EPub
- **Stdin processing** — Accepts piped input with file-type hint (`-x EXTENSION`), charset hint (`-c CHARSET`), or MIME type hint (`-m MIME_TYPE`)
- **Azure Document Intelligence** — Optional `-d` flag with `-e ENDPOINT` for better PDF extraction on complex documents
- **Plugin support** — `--use-plugins` and `--list-plugins` for third-party plugin enablement

### Requirements

- `**uvx`** (from the `uv` Python package manager) must be available in PATH — installs dependencies on first run, subsequent runs are faster
- For Azure Document Intelligence: a valid Azure endpoint and credentials
- No OS restrictions; works on any platform where `uvx` is available

### Output

- Markdown text written to stdout or to a specified output file (`-o OUTPUT`)
- Output preserves document structure: headings, tables, lists, links
- For piped stdin: output goes to stdout or is redirected to a file

## Skill: marketing-mode

**Path:** `/usr/lib/node_modules/openclaw/skills/marketing-mode/SKILL.md`

### Purpose

Comprehensive marketing knowledge base combining 23 marketing disciplines into a single skill. Covers strategy, psychology, content, SEO, conversion optimization, and paid growth. Activates a marketer persona ("Mark the Marketer") to deliver structured, framework-driven marketing guidance.

### Tools Used

- (No direct tool calls) — Primarily a knowledge/reference skill; all output is delivered as structured text in the chat context

### Capabilities

- **140+ marketing tactics** across 14 categories: Content & SEO, Competitor & Comparison, Free Tools & Engineering, Paid Advertising, Social Media & Community, Email Marketing, Partnerships & Programs, Events & Speaking, PR & Media, Launches & Promotions, Product-Led Growth, Unconventional & Creative, Platforms & Marketplaces, Developer & Technical, Audience-Specific
- **5-Phase Launch Framework** — Internal → Alpha (private beta) → Beta (public preview) → Early Access → Full Launch
- **Pricing Strategy** — Research methods, tier structures, value metrics, monetization optimization
- **70+ psychological mental models** — First principles, JTBD, Pareto, Hick's Law, AIDA, scarcity, loss aversion, anchoring, endowment effect, IKEA effect, mere exposure, Zeigarnik effect, prospect theory, and more
- **SEO Audit Framework** — Crawlability, indexation, Core Web Vitals (LCP/INP/CLS), on-page, E-E-A-T
- **12 Programmatic SEO Playbooks** — Location pages, comparison pages, integration pages, use case pages, problem pages, industry pages, review/alternatives, calculators, templates, glossary, checklists, quiz/assessment
- **Schema Markup** — Organization, Product/Service, FAQPage, HowTo, Review/BreadcrumbList, LocalBusiness
- **Copywriting Frameworks** — AIDA, PAS, Before/After/Bridge, ACCA, Hero's Journey
- **7-Sweep Copy Editing** — Clarity, voice, proof, impact, emotion, format, authenticity
- **CRO Elements** — Value proposition, trust signals, CTA optimization, friction analysis
- **Channel Strategy** — Google Ads, Meta/Facebook, LinkedIn, analytics/tracking (UTM, GA4, GTM), referral program design, free tool strategy
- **Email Sequences** — Welcome, nurture, onboarding, win-back, re-engagement

### Requirements

- `**node`** and `**npm`** — Required bins (listed in skill metadata under `requires.bins`)
- Activated via `clawdhub` skill install (skill slug: `marketing-mode`)

### Output

- Structured marketing guidance delivered as formatted text in the chat
- Quick reference tables mapping marketing challenges to relevant frameworks
- Discovery questions for marketing briefs
- 23 named sub-skills referenced for deep-dives: marketing-ideas, marketing-psychology, launch-strategy, pricing-strategy, seo-audit, programmatic-seo, schema-markup, competitor-alternatives, copywriting, copy-editing, social-content, email-sequence, page-cro, signup-flow-cro, form-cro, onboarding-cro, paywall-cro, popup-cro, ab-test-setup, paid-ads, analytics-tracking, referral-program, free-tool-strategy

## Skill: mechanic

**Path:** `/usr/lib/node_modules/openclaw/skills/mechanic/SKILL.md`

### Purpose

Vehicle maintenance tracker and mechanic advisor. Tracks mileage, service intervals, fuel economy, costs, warranties, and recalls. Decodes VINs to auto-populate vehicle specs, researches manufacturer schedules, estimates costs, projects service dates, monitors NHTSA recalls, tracks fuel economy with anomaly detection, manages warranties, generates pre-trip/seasonal checklists, and supports cost-per-mile analysis. Supports any vehicle type.

### Tools Used

- `**exec`** — Runs `uv` commands for Python environment setup; runs cron job agent sessions
- `**write`** — Creates `state.json` and `<key>-schedule.json` data files in `<workspace>/data/mechanic/`
- `**read**` — Reads `state.json` and schedule files on skill load
- `**edit**` — Updates state files (mileage history, service history, fuel logs, etc.)
- `**web_fetch**` / `**web_search**` — Used indirectly to research manufacturer schedules and look up vehicle specs
- `**openclaw cron**` — Schedules and manages the weekly mileage check cron job
- `**memory_***` tools — Used conditionally for audit trail logging (only when user opts in)

### Capabilities

- **Vehicle management** — Add/update/remove vehicles (cars, trucks, motorcycles, dirt bikes, ATVs, RVs, boats, trailers); keyed by short slug
- **VIN decode** — Frees NHTSA VPIC API (`DecodeVinValues`) to auto-populate year, make, model, engine, transmission, drive type, specs, emergency info; supports US-market vehicles, trailers/RVs/motorcycles may have limited coverage
- **NHTSA recall monitoring** — Checks open recalls by VIN or by make/model/year; stores open/completed recalls per vehicle; monthly cron check
- **Service schedule management** — Per-vehicle JSON schedule with `interval_miles`, `interval_months`, `interval_hours`, `interval_rides`; priority levels (critical/high/medium/low); cost estimates for DIY/shop/dealer
- **Mileage tracking** — Chronological history; mileage projection for service dates; weekly cron check with per-vehicle frequency (weekly/biweekly/monthly/quarterly)
- **Fuel/MPG tracking** — Fill-up logging with MPG calculation; rolling average; anomaly detection (>15% below rolling average triggers alert)
- **Warranty tracking** — Factory, extended, parts/labor warranties; expiration alerts (3 months or 3,000 miles before end)
- **Pre-trip/seasonal checklists** — Vehicle-specific checklists combining due services, weather, trip type, and seasonal items; towing checklist includes truck + trailer/RV items
- **Service provider tracking** — Global provider list with specialties, rating, contact info; per-service-provider warranty tracking
- **Tax deduction integration** — Business-use percentage tracking; deductible portion calculation; optional integration with `tax-professional` skill
- **Emergency info card** — Quick-access vehicle specs: VIN, insurance, roadside, tire sizes/pressures, oil type/capacity, coolant, fuel type, tow rating, GVWR/GCWR, key fob battery
- **Cost-per-mile analysis** — Maintenance cost/mile, fuel cost/mile, total operating cost; fleet overview across multiple vehicles
- **Service review output** — Full report with recall alerts, warranty alerts, overdue/due-soon services with cost estimates, projected schedule, fuel economy, spending summary, cost per mile

### Requirements

- `**uv`** (Python package manager) for Python environment setup
- `python>=3.11` required by the skill
- **NHTSA VPIC API** — Free, no API key, unlimited; for US-market vehicles
- **OpenClaw cron** — `openclaw cron add` for weekly mileage check and monthly recall check
- User timezone from `<workspace>/USER.md` for cron scheduling
- Workspace write access for `data/mechanic/` directory

### Output

- Structured service reports in chat (recall alerts, overdue/due-soon with cost estimates, fuel economy, warranty alerts, spending summaries, cost-per-mile)
- `state.json` — All vehicle state in `<workspace>/data/mechanic/`
- `<key>-schedule.json` — Per-vehicle service schedule
- Cron job delivers periodic check-in messages to the user's chat channel

## Skill: mermaid-diagrams

**Path:** `/usr/lib/node_modules/openclaw/skills/mermaid-diagrams/SKILL.md`

### Purpose

Creates software diagrams using Mermaid's text-based syntax. Triggers include requests to diagram, visualize, model, map out, or show the flow of a system. Mermaid renders diagrams from simple text definitions, making them version-controllable and easy to maintain alongside code.

### Tools Used

- (No direct tool calls) — This is a syntax reference/knowledge skill; the agent generates Mermaid syntax text which is then rendered by external tools (GitHub, VS Code, Mermaid Live Editor, etc.)

### Capabilities

- **8 core diagram types:**
  - **Class Diagrams** — Domain modeling, OOP design, entity relationships
  - **Sequence Diagrams** — API flows, auth flows, component interactions
  - **Flowcharts** — Processes, algorithms, decision trees, user journeys
  - **ERDs** — Database schemas, table relationships, data modeling
  - **C4 Diagrams** — System context, containers, components, architecture
  - **State Diagrams** — State machines, lifecycle states
  - **Git Graphs** — Branching strategies
  - **Gantt Charts** — Project timelines, scheduling
- **Configuration and theming** — Frontmatter config blocks, theme variables, layout options (dagre default, ELK for complex), look options (classic, hand-drawn)
- **Export options** — GitHub/GitLab native rendering, VS Code extension, Mermaid Live Editor (PNG/SVG export), Mermaid CLI (`mmdc`)
- **Reference subdocuments** — References to `references/class-diagrams.md`, `references/sequence-diagrams.md`, `references/flowcharts.md`, `references/erd-diagrams.md`, `references/c4-diagrams.md`, `references/advanced-features.md`

### Requirements

- `**npx clawhub@latest install mermaid-diagrams`** — Installation command for OpenClaw/Moltbot/Clawbot
- For live rendering: Mermaid Live Editor at [https://mermaid.live](https://mermaid.live), VS Code Mermaid extension, or any platform with native Mermaid support (GitHub, GitLab, Notion, Obsidian, Confluence)
- For CLI export: `npm install -g @mermaid-js/mermaid-cli` and `mmdc`

### Output

- Mermaid syntax text (`.mmd` files or inline in Markdown) delivered directly in chat
- Diagrams render in any Mermaid-aware platform (no native rendering in OpenClaw chat itself)
- Key constraints: No more than 15 nodes per diagram, no unlabeled arrows, all diagrams need title/caption, pair with prose explaining the "why"

## Skill: moltspaces

**Path:** `/usr/lib/node_modules/openclaw/skills/moltspaces/SKILL.md`

### Purpose

Enables the agent to join audio room spaces on Moltspaces (moltspaces.com) — a voice-first social space for AI agents and humans. The agent can register, configure voice, prepare personality/persona, and launch a bot into a room to participate in audio conversations on a given topic.

### Tools Used

- `**exec`** — Runs `curl` commands for API calls (voice fetching, agent registration, room search, token retrieval); runs `uv run scripts/bot.py` to launch the bot; runs `pkill` to stop the bot
- `**write`** — Creates `assets/personality.md` and `assets/notes.md` configuration files
- `**read**` — Reads `assets/personality.md` and `assets/notes.md` when launching the bot

### Capabilities

- **Agent registration** — Registers a new agent on Moltspaces via `POST /agents/register`; returns `api_key`, `agent_id`, `claim_url`; user must verify X and email, then post a verification tweet to claim the agent
- **ElevenLabs voice selection** — Fetches available voices via `GET /v1/voices`; selects the best match for the agent's personality or asks the user to choose
- **Environment configuration** — Interactive setup of `.env` file with `MOLTSPACES_API_KEY`, `MOLT_AGENT_ID`, `MOLT_AGENT_NAME`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, optional `ELEVENLABS_VOICE_ID`
- **Personality preparation** — Asks user for agent tone/style, traits, background; saves to `assets/personality.md`
- **Notes/talking points preparation** — Creates `assets/notes.md` with hook/context, problem landscape, core framework (3-5 pillars), case studies, future-cast
- **Room management** — Search for existing rooms (`GET /rooms/:room_name`), get token to join a specific room (`POST /rooms/:roomName/token`), create a new room (`POST /rooms`)
- **Bot launch** — Runs `uv run scripts/bot.py --url <room_url> --token <daily_token> --topic <topic> --personality <personality_file>` as a background process; logs to `bot.log`
- **Bot shutdown** — Stops the background bot process via `ps aux | grep bot.py` + `kill <PID>` or `pkill -f bot.py`

### Requirements

- `**uv`** (Python package manager) — must be installed
- `**python>=3.11`** — required for the skill
- `**uv sync**` — installs Python dependencies from `pyproject.toml`
- **API keys required:**
  - `OPENAI_API_KEY` (from OpenAI platform)
  - `ELEVENLABS_API_KEY` (from elevenlabs.io)
  - `MOLTSPACES_API_KEY` (from Moltspaces agent registration)
- Moltspaces account and verification via X and email
- Background process capable environment (for `&` backgrounding of the bot)

### Output

- Text feedback during setup (registration results, voice list, room info)
- Bot runs as background process; output goes to `bot.log 2>&1 &`
- Claim URL sent to user to complete agent verification

*End of Batch 3 skill map. 11 skills documented.*

## Skill: news-summary

**Path:** `/usr/lib/node_modules/openclaw/skills/news-summary/SKILL.md`

### Purpose

Fetch and summarize news from trusted international RSS feeds, with optional voice summary generation. Designed to give users a daily briefing of top stories grouped by region or topic.

### Tools Used

- `**exec`** — `curl` to fetch RSS feeds from multiple sources
- `**tts`** (via curl to OpenAI `/v1/audio/speech`) — for voice summary output

### Capabilities

- Fetch world headlines from BBC (primary), Reuters, NPR, and Al Jazeera RSS feeds
- Parse and extract titles/descriptions from XML RSS responses using `grep`/`sed`
- Group stories by region or topic (World, Business, Tech)
- Produce concise text summaries (5–8 top stories)
- Generate spoken audio summaries via OpenAI TTS (tts-1-hd, voice: onyx)
- Balance Western and Global South perspectives

### Requirements

- `curl` availability on the system
- Optional: `OPENAI_API_KEY` env var (for voice summary generation via OpenAI TTS endpoint)

### Output

- Formatted text summary with emoji headers per category (e.g. "WORLD", "BUSINESS", "TECH")
- Optionally: MP3 audio file sent as voice message (when voice output is requested)

## Skill: nextjs-expert

**Path:** `/usr/lib/node_modules/openclaw/skills/nextjs-expert/SKILL.md`

### Purpose

Comprehensive Next.js 15 App Router specialist skill for building production-grade full-stack applications. Provides guidance on routing, layouts, Server/Client Components, data fetching, caching, Server Actions, Route Handlers, authentication (NextAuth v5 / Auth.js), middleware, and anti-patterns.

### Tools Used

- `**exec`** — inline script examples; used for running verification commands
- No external API calls; entirely knowledge-based guidance

### Capabilities

- App Router file conventions and route structure
- Dynamic routes, catch-all segments, optional catch-all
- Parallel routes and intercepting routes (slots)
- Server Components vs Client Components decision framework
- Server Actions with Zod validation, `useFormState`, `useFormStatus`, optimistic updates
- Route Handlers (GET/POST/DELETE) with streaming and SSE support
- NextAuth.js v5 / Auth.js setup: providers, JWT/session callbacks, middleware protection, server-side auth checks
- `generateStaticParams` and `generateMetadata` (static and dynamic)
- Layout nesting, route groups for multiple root layouts
- Caching strategies: `revalidatePath`, `revalidateTag`, `cache()`, per-fetch options
- Streaming with `Suspense` and loading states / error boundaries
- Route segment config: `dynamic`, `revalidate`, `runtime`, `maxDuration`

### Requirements

- No env vars, bins, or external services required
- Pure knowledge/skill reference; no API dependencies

### Output

- Code examples (TypeScript/TSX) returned directly as chat text
- Architecture guidance, patterns, and anti-patterns documented in full

## Skill: node-connect

**Path:** `/usr/lib/node_modules/openclaw/skills/node-connect/SKILL.md`

### Purpose

Diagnose OpenClaw Android, iOS, or macOS node pairing failures, QR/setup code issues, routing problems, auth failures, and connection failures. Finds the correct route from node to gateway and fixes pairing/auth.

### Tools Used

- `**exec`** — runs `openclaw` CLI commands to inspect gateway config, QR output, device list, node status
- `**exec`** — Tailscale CLI (`tailscale status --json`) when Tailscale is part of the topology

### Capabilities

- Inspect gateway configuration (`gateway.mode`, `gateway.bind`, `gateway.tailscale.mode`, `gateway.remote.url`, `gateway.auth.mode`, `gateway.auth.allowTailscale`)
- Inspect plugin config for public URL (`plugins.entries.device-pair.config.publicUrl`)
- Generate and inspect QR setup codes (`openclaw qr --json`, `openclaw qr --remote --json`)
- List pending device pairings and approve them (`openclaw devices list`, `openclaw devices approve --latest`)
- Check node status (`openclaw nodes status`)
- Determine correct topology: same machine, same LAN, Tailscale tailnet, or public URL/reverse proxy
- Diagnose root causes: loopback-only binding, missing tailnet IP, stale setup codes, wrong auth expectations
- Approve pending device pairings when routing and auth have succeeded

### Requirements

- `openclaw` CLI installed and accessible
- Tailscale CLI (`tailscale`) if Tailscale route is involved
- No env vars required; relies on OpenClaw config and CLI commands

### Output

- One concrete diagnosis and one fix prescription per response
- Asks clarifying questions if setup is ambiguous rather than guessing

## Skill: notion

**Path:** `/usr/lib/node_modules/openclaw/skills/notion/SKILL.md`

### Purpose

Full Notion API integration for creating, reading, updating, and managing pages, databases (data sources), and blocks. Supports search, property updates, block appending, and data source queries.

### Tools Used

- `**exec`** — `curl` for all Notion API HTTP calls

### Capabilities

- Search pages and data sources by query
- Get a page and its block children (page content)
- Create pages inside a database (using `database_id` in parent)
- Query a data source (database) with filter and sort options
- Create a data source (database) inside a page with properties
- Update page properties (select, checkbox, date, etc.)
- Append blocks to a page (paragraphs, up to 100 children per request, 2 levels nesting)
- All standard Notion property types: title, rich_text, select, multi_select, date, checkbox, number, url, email, relation

### Requirements

- `NOTION_API_KEY` env var (API key starts with `ntn`_ or `secret_`)
- Notion integration must be created at `notion.so/my-integrations`
- Target pages/databases must be shared with the integration (via "Connect to" menu)
- `curl` availability
- Notion-Version header `2025-09-03` (latest); databases are now "data sources" in this version
- Rate limit: ~3 req/s; handle `429 rate_limited` with `Retry-After`
- Max payload: 1000 block elements, 500KB per request
- Max block append: 100 children per request, up to 2 nesting levels

### Output

- JSON responses from Notion API returned as structured text (title/property summaries, block content listings)

## Skill: ontology

**Path:** `/usr/lib/node_modules/openclaw/skills/ontology/SKILL.md`

### Purpose

Typed knowledge graph system for structured agent memory and composable skills. Enables creating/querying entities (Person, Project, Task, Event, Document), linking related objects, enforcing constraints, planning multi-step actions as graph transformations, and cross-skill state sharing.

### Tools Used

- `**exec`** — runs `python3 scripts/ontology.py` with subcommands: `create`, `query`, `get`, `related`, `relate`, `validate`, `schema-append`, `list`
- **File I/O** — reads/writes `memory/ontology/graph.jsonl` (append-only entity store) and `memory/ontology/schema.yaml` (constraints)
- **read/write** — for reading schema references and managing storage files

### Capabilities

- Entity CRUD: create, query, get by ID, relate, validate
- Core types: Person, Organization, Project, Task, Goal, Event, Location, Document, Message, Thread, Note, Account, Device, Credential, Action, Policy
- Relation management with type constraints and cardinality
- Schema constraints: required properties, enum validation, forbidden properties (e.g. no raw secrets in Credential), acyclicity checks, `end >= start` for Event
- Append-only mutation log (`graph.jsonl`) preserving history
- Graph transformation planning (model multi-step plans as a sequence of `CREATE`/`RELATE` operations)
- Cross-skill communication via shared ontology store
- Causal inference integration (logging ontology mutations as causal actions)
- Skill contract declarations (reads/writes/preconditions/postconditions)
- SQLite migration path for complex graphs

### Requirements

- `python3` availability
- `memory/ontology/` directory (created on first use)
- `memory/ontology/graph.jsonl` and `memory/ontology/schema.yaml` (created on init)
- Optional: `scripts/ontology.py` CLI tool for schema and CRUD operations

### Output

- Entity and relation data returned as structured text/JSON
- Validation results report constraint violations
- Planning output as a sequence of graph operation steps

## Skill: openai-whisper-api

**Path:** `/usr/lib/node_modules/openclaw/skills/openai-whisper-api/SKILL.md`

### Purpose

Transcribe audio files via the OpenAI Audio Transcriptions API (Whisper model). Simple wrapper around `curl` with configurable model, language, output path, and prompt.

### Tools Used

- `**exec`** — runs `{baseDir}/scripts/transcribe.sh` (bash script using curl)
- `**exec`** — direct `curl` calls to `https://api.openai.com/v1/audio/transcriptions`

### Capabilities

- Transcribe audio files (m4a, ogg, etc.) to text using OpenAI Whisper-1 model
- Specify language (e.g. `--language en`)
- Provide transcription prompt for speaker names or context (`--prompt`)
- Output as plain text (`.txt`) or JSON
- Configurable output file path
- Support `OPENAI_BASE_URL` for OpenAI-compatible proxies or local gateways

### Requirements

- `OPENAI_API_KEY` env var (or configured in OpenClaw config under `skills.openai-whisper-api.apiKey`)
- `curl` availability (installable via brew on macOS)
- Audio file to transcribe
- `scripts/transcribe.sh` in the skill's base directory

### Output

- Plain text transcription to stdout or specified output file
- JSON response mode available (`--json`)

## Skill: openrouter-transcribe

**Path:** `/usr/lib/node_modules/openclaw/skills/openrouter-transcribe/SKILL.md`

### Purpose

Transcribe audio files via OpenRouter using audio-capable models (Gemini 2.5 Flash, GPT-4o-audio-preview, etc.). Converts audio to WAV (mono, 16kHz), base64-encodes, and sends via OpenRouter chat completions with `input_audio` content.

### Tools Used

- `**exec`** — runs `{baseDir}/scripts/transcribe.sh`
- `**exec`** — uses `ffmpeg` for audio format conversion, `base64` for encoding, `jq` for JSON extraction

### Capabilities

- Transcribe audio to text via OpenRouter's chat completions API
- Support any audio-capable model (default: `google/gemini-2.5-flash`)
- Custom caller identifier (`--title`) for OpenRouter dashboard tracking
- Custom instructions via `--prompt`
- Audio format conversion via ffmpeg (WAV, mono, 16kHz)
- Writes temp files to avoid shell argument limits with large audio
- Raw response debugging on empty response

### Requirements

- `OPENROUTER_API_KEY` env var (or configured in `~/.clawdbot/clawdbot.json`)
- `curl`, `ffmpeg`, `base64`, `jq` binaries
- Audio file to transcribe
- `scripts/transcribe.sh` in the skill's base directory

### Output

- Plain text transcription to stdout
- Debug info on failure (dumps raw response)

## Skill: plan2meal

**Path:** `/usr/lib/node_modules/openclaw/skills/plan2meal/SKILL.md`

### Purpose

Manage recipes and grocery lists in Plan2Meal via chat commands. Supports adding recipe URLs, listing/searching/showing/deleting recipes, and creating/managing grocery lists.

### Tools Used

- `**exec`** — runs `clawdhub` CLI commands (`clawdhub install plan2meal`, etc.) and Plan2Meal CLI commands directly (`plan2meal login`, `plan2meal add <url>`, etc.)

### Capabilities

- Authenticate to Plan2Meal (`plan2meal login`/`logout`)
- Add recipe from URL (`plan2meal add <url>`)
- List all recipes (`plan2meal list`)
- Search recipes by term (`plan2meal search <term>`)
- Show recipe details by ID (`plan2meal show <id>`)
- Delete recipe by ID (`plan2meal delete <id>`)
- List grocery lists (`plan2meal lists`)
- Show grocery list by ID (`plan2meal list-show <id>`)
- Create grocery list (`plan2meal list-create <name>`)
- Add recipe to grocery list (`plan2meal list-add <listId> <recipeId>`)
- Display help (`plan2meal help`)

### Requirements

- `clawdhub` CLI installed
- Required env vars: `CONVEX_URL`, `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, `GITHUB_CALLBACK_URL`, `CLAWDBOT_URL`
- Optional env vars: `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `AUTH_APPLE_ID`, `AUTH_APPLE_SECRET` and their callback URLs
- `ALLOW_DEFAULT_BACKEND=true` only if intentionally using shared backend (`https://gallant-bass-875.convex.cloud`)

### Output

- Structured command output with IDs, counts, links, and error messages
- Must disclose shared backend usage if relevant
- Never expose secrets/tokens in output

## Skill: polymarket

**Path:** `/usr/lib/node_modules/openclaw/skills/polymarket/SKILL.md`

### Purpose

Query and trade Polymarket prediction markets from the terminal — check odds, trending markets, search events, view order books, place trades, and manage positions.

### Tools Used

- `**exec`** — runs `python3 {baseDir}/scripts/polymarket.py` with various subcommands
- `**exec`** — for the optional Polymarket CLI (`polymarket-cli`) installation via curl script

### Capabilities

- **Read-only** (no CLI required): trending markets, market search, event lookup by slug, markets by category (politics, crypto, etc.)
- **Order book & price history** (CLI required, no wallet): view order book for a token, price history with interval
- **Wallet management** (CLI required): setup, show, balance (global and per token)
- **Trading** (CLI + wallet required): buy/sell limit orders, market orders, all require `--confirm` flag
- **Orders & positions** (CLI + wallet required): list open orders, cancel by ID or all, view positions

### Requirements

- Read-only commands: no install needed, uses public Gamma API (`https://gamma-api.polymarket.com`)
- Trading/order book/price history: requires [Polymarket CLI](https://github.com/Polymarket/polymarket-cli) installed
- Trading: requires wallet configured with private key in `~/.config/polymarket/config.json`
- MATIC for gas fees (on-chain operations)

### Output

- Trending/search results as formatted market data
- Order book as structured bid/ask data
- Trade confirmations and previews (without `--confirm`)
- Wallet balance and position reports

## Skill: powerpoint-pptx

**Path:** `/usr/lib/node_modules/openclaw/skills/powerpoint-pptx/SKILL.md`

### Purpose

Create, inspect, and edit Microsoft PowerPoint presentations and `.pptx` decks with reliable layouts, templates, placeholders, notes, charts, and visual QA. Handles the full OOXML structure including slides, layouts, masters, media, notes, and comments.

### Tools Used

- `**exec`** — for running any inspection/build scripts; PowerPoint files are zip archives containing XML
- `**read`** — to inspect slide XML, layout definitions, master slides, notes
- `**write**` — to create/modify PPTX zip contents
- `**canvas**` — for rendered slide inspection and visual QA
- Implicit file I/O for PPTX creation/editing

### Capabilities

- Inventory existing decks before editing (count layouts, placeholders, notes, comments, media, typography patterns)
- Extract text content from decks for inspection
- Match content to actual placeholders (avoid wrong shape targeting)
- Preserve deck visual language (theme, master, layout fonts/colors/spacing)
- Content QA and visual QA (separate failure classes; overlapping, clipped, theme-mismatched output)
- Template-driven editing: reuse good existing slides rather than rebuilding
- Handle chart, table, and image-heavy slides with appropriate layouts
- Manage speaker notes, comments, linked media outside visible surface
- Cross-template consistency when combining slides from multiple sources

### Requirements

- No external bins or env vars required
- OS: Linux, macOS, Windows
- PowerPoint file access (read/write local files)
- Visual QA may require rendering capability (canvas/browser)

### Output

- Created/edited `.pptx` files
- Content extraction and inspection reports
- Visual QA feedback (layout issues, text overflow, placeholder leftovers, theme mismatches)

## Skill: productivity

**Path:** `/usr/lib/node_modules/openclaw/skills/productivity/SKILL.md`

### Purpose

Build and maintain a personal productivity operating system in `~/productivity/`. Covers goals, projects, tasks, habits, planning, reviews, commitments, focus sessions, routines, and inbox triage — adapted to the user's real context (student, executive, freelancer, parent, creative, burnout, ADHD, remote, manager, etc.).

### Tools Used

- `**read`** — to read reference files (`setup.md`, `memory-template.md`, `system-template.md`, `frameworks.md`, `traps.md`, situation guides in `situations/`)
- `**write`** — to create/update `~/productivity/` files only after explicit user approval
- `**exec**` — none; no external network calls, no CLI commands

### Capabilities

- Initial setup: create the full `~/productivity/` directory structure with all subfolders and template files
- System routing: detect when productivity skill should activate vs. generic advice
- Goal → Project → Milestones → Next Actions conversion
- Weekly and monthly review frameworks
- Habit tracking (active habits + friction notes)
- Focus block planning (deep work + recovery)
- Startup and shutdown routine design
- Inbox capture and triage
- Commitment tracking (promises + delegated)
- Context-specific guidance for: student, executive, freelancer, parent, creative, burnout, entrepreneur, ADHD, remote, manager, habits, guilt
- Quick reference queries for any system layer

### Requirements

- No external bins, env vars, or network access required
- Creates `~/productivity/` directory on setup
- Writes files only after explicit user approval
- No external services; fully local

### Output

- Structured productivity files in `~/productivity/` (dashboard, goals, projects, tasks, habits, planning, reviews, commitments, focus, routines, someday)
- Productivity advice and planning frameworks delivered as chat text
- Situation-specific guidance drawn from included reference files

*End of Batch 4 — 11 skills analyzed.*

## Skill: relationship-skills

**Path:** `/usr/lib/node_modules/openclaw/skills/relationship-skills/SKILL.md`

### Purpose

Provides guidance and frameworks for improving interpersonal relationships — covering communication, conflict resolution, date ideas, relationship health tracking, and connection-building. Designed as a consultative reference the agent uses when the user asks about relationship dynamics, conversations, or bonding.

### Tools Used

- **No direct OpenClaw tool calls** — purely advisory/instructional content. The agent applies the frameworks verbally when triggered by keywords.

### Capabilities

- Communication frameworks (I-statements, active listening, needs expression, boundary setting)
- Conflict de-escalation techniques and structured problem-solving
- Curated date ideas tailored to budget and novelty preferences
- Relationship check-in prompts and conversation starters
- Pattern tracking for recurring topics and connection quality
- Privacy-preserving (all data stays local on the machine)

### Requirements

- No binaries, env vars, or external services required
- No OS restrictions — works on all platforms

### Output

- Structured advice, frameworks, and prompts returned as conversational text
- No file creation, no external calls — outputs are agent-generated responses

## Skill: self-improving

**Path:** `/usr/lib/node_modules/openclaw/skills/self-improving/SKILL.md`

### Purpose

Enables the agent to autonomously learn from corrections, self-reflect after significant work, and compound knowledge over time via a tiered local file system. Memory is permanent and organized across hot/warm/cold tiers, replacing the need for manual maintenance.

### Tools Used

- **exec** — for reading/writing memory files in `~/self-improving/`
- **read / write / edit** — for modifying `memory.md`, `corrections.md`, `projects/`, `domains/`, `archive/`, `heartbeat-state.md`
- No network tools, no calendar/email access

### Capabilities

- Logs user corrections and derives reusable lessons
- Self-reflection after multi-step tasks with structured `CONTEXT/REFLECTION/LESSON` format
- Pattern promotion/demotion across three tiers (HOT ≤100 lines → WARM → COLD)
- Namespace isolation (project/domain/global patterns)
- Conflict resolution when patterns contradict
- Graceful degradation when context limits are hit
- Memory stats, export (ZIP), and deletion by the user
- Heartbeat state maintenance for recurring self-review
- Transparent provenance tracking ("Using X from projects/foo.md:12")

### Requirements

- `~/self-improving/` directory created by running `setup.md` if absent
- Optional: `AGENTS.md`, `SOUL.md`, `HEARTBEAT.md` workspace integration for heartbeat steering
- No credentials, no extra binaries
- OS: linux, darwin, win32

### Output

- Lessons stored in local files (`~/self-improving/`)
- Agent cites sources from memory when applying rules
- Memory stats presented as structured text on request

## Skill: self-reflection

**Path:** `/usr/lib/node_modules/openclaw/skills/self-reflection/SKILL.md`

### Purpose

Triggered on heartbeat intervals, this skill checks whether self-reflection is due and logs new insights. It is a lightweight, cron-style reflection engine that records lessons and tracks reflection statistics over time.

### Tools Used

- **exec** — runs the `self-reflection` CLI commands (`check`, `log`, `read`, `stats`, `reset`)
- Required bins: `jq`, `date`
- **read** (implicit via exec output) — memory files are read/written through the CLI

### Capabilities

- Checks whether reflection is due (returns OK or ALERT)
- Logs new reflections with a tag, miss description, and fix (three-argument format)
- Reads the last N reflections (default 5)
- Shows reflection statistics
- Resets the heartbeat timer
- Integrates with OpenClaw heartbeat (via `HEARTBEAT.md`)

### Requirements

- `jq` and `date` binaries installed
- OpenClaw heartbeat enabled in `~/.openclaw/openclaw.json`
- `~/.openclaw/self-reflection.json` config file (optional overrides for threshold, memory file, state file, max entries)

### Output

- Structured text responses from CLI commands (stats, read output)
- Lessons written to `~/workspace/memory/self-review.md`
- State tracked in `~/.openclaw/self-review-state.json`

## Skill: session-logs

**Path:** `/usr/lib/node_modules/openclaw/skills/session-logs/SKILL.md`

### Purpose

Searches and analyzes the agent's own conversation history stored in session JSONL files. Enables the user to query what was said in prior/parent conversations by parsing and filtering structured session logs.

### Tools Used

- **exec** — runs `jq`, `rg` (ripgrep), `head`, `tail`, `sort`, `awk`, `ls` against session files
- Required bins: `jq`, `rg`

### Capabilities

- List all sessions by date and size
- Filter sessions from a specific date
- Extract user messages, assistant responses, or tool calls from any session
- Search across all sessions for a keyword or phrase
- Compute total cost per session
- Daily cost aggregation across all sessions
- Count messages and tokens per session
- Tool usage breakdown (which tools were called, how often)
- Fast text-only keyword extraction from session logs
- Access via `sessions.json` index and `sessions/<session-id>.jsonl` files under `$OPENCLAW_STATE_DIR/agents/<agentId>/sessions/`

### Requirements

- `jq` and `ripgrep` (rg) binaries installed (homebrew install scripts provided)
- Session logs stored at `$OPENCLAW_STATE_DIR/agents/<agentId>/sessions/`
- OS: darwin (homebrew install hints), linux, win32

### Output

- Tabular or line-oriented text output from shell commands
- Structured data (costs, dates, counts) printed to stdout

## Skill: sherpa-onnx-tts

**Path:** `/usr/lib/node_modules/openclaw/skills/sherpa-onnx-tts/SKILL.md`

### Purpose

Provides local, offline text-to-speech using the `sherpa-onnx` CLI — no cloud dependency. Installs the sherpa-onnx runtime and a voice model, then exposes a wrapper script for generating WAV audio from text input.

### Tools Used

- **exec** — downloads and extracts runtime/model tarballs, runs the `sherpa-onnx-tts` CLI binary
- **write / edit** — for patching the OpenClaw config file with env vars (`SHERPA_ONNX_RUNTIME_DIR`, `SHERPA_ONNX_MODEL_DIR`)

### Capabilities

- Downloads and installs the sherpa-onnx runtime for darwin/linux/win32 (universal2/x64)
- Downloads and installs the en_US lessac high-quality voice model
- Generates WAV audio from text input via the CLI wrapper
- Supports model file override (`--model-file`), tokens file (`--tokens-file`), data dir (`--data-dir`)
- Configurable via `SHERPA_ONNX_MODEL_FILE` env var for multi-model setups

### Requirements

- OS: darwin, linux, win32
- Env vars (must be set in OpenClaw config):
  - `SHERPA_ONNX_RUNTIME_DIR` — path to extracted runtime
  - `SHERPA_ONNX_MODEL_DIR` — path to the model directory
- Optional: `SHERPA_ONNX_MODEL_FILE` for multi-onnx model dirs
- State dir: `$OPENCLAW_STATE_DIR/tools/sherpa-onnx-tts/` (default `~/.openclaw/tools/sherpa-onnx-tts/`)
- Wrapper script added to PATH via `{baseDir}/bin/`

### Output

- WAV audio file written to the path specified with `-o`
- CLI exit code indicates success/failure

## Skill: skill-creator

**Path:** `/usr/lib/node_modules/openclaw/skills/skill-creator/SKILL.md`

### Purpose

Guides the agent (and user) through the complete process of creating, editing, packaging, and iterating on OpenClaw skills. Provides design principles, structural templates, and automation scripts for building high-quality, distributable skill packages.

### Tools Used

- **exec** — runs Python scripts: `scripts/init_skill.py` and `scripts/package_skill.py`
- **read** — reads bundled reference files (`references/workflows.md`, `references/output-patterns.md`)
- **write** — creates skill directory, SKILL.md, scripts, references, and assets
- No external network calls

### Capabilities

- Creates skill directory structure from scratch via `init_skill.py`
- Writes SKILL.md with YAML frontmatter (`name`, `description` only) and body content
- Defines bundled resources: `scripts/`, `references/`, `assets/`
- Packages skills into `.skill` zip files via `package_skill.py` (includes validation: YAML format, naming conventions, file organization, symlink rejection)
- Guides on progressive disclosure design (metadata → SKILL.md body → bundled resources)
- Enforces best practices: concise instructions, appropriate degrees of freedom, no extraneous files (no README/CHANGELOG)
- Skill naming: lowercase/hyphens only, ≤64 chars, verb-led preferred

### Requirements

- Python 3 environment for running `init_skill.py` and `package_skill.py`
- No external binaries beyond Python
- Scripts live in the skill's `scripts/` subdirectory

### Output

- Skill directory structure on disk
- Validated `.skill` package file (zip with `.skill` extension)
- Exit codes from packaging script (success or validation error report)

## Skill: skill-hub

**Path:** `/usr/lib/node_modules/openclaw/skills/skill-hub/SKILL.md`

### Purpose

Unified skill discovery, security vetting, and installation management. Searches 3000+ curated skills from the ClawHub registry and awesome-openclaw-skills catalog. Scores credibility, scans for prompt injection/malicious patterns, and manages installation lifecycle.

### Tools Used

- **exec** — runs Python scripts: `skill-hub-search.py`, `skill-hub-vet.py`, `skill-hub-status.py`, `skill-hub-quick-check.py`, `skill-hub-table-export.py`, `skill-hub-sync.py`
- **read** — reads skill files during security vetting

### Capabilities

- Search skills by keyword, category, credibility score, or live ClawHub results
- Show only installed or only unvetted skills (discovery mode)
- Security vet single skill, all installed, by category, or top N unvetted
- Status dashboard showing installed vs catalog coverage, unvetted warnings
- Quick check via GitHub API for new skills (without full download)
- Browse full catalog as formatted table (terminal or markdown)
- Full sync from GitHub awesome-list with credibility recomputation
- ClawHub install integration: `npx clawhub@latest install <slug>`

### Requirements

- `gh` CLI for quick-check (GitHub API access)
- Python 3 for all scripts
- Network access for live search and sync operations

### Output

- Structured text/table output from search, status, and browse commands
- Vet results: security pass/fail with breakdown
- Install commands printed as instructions for the user to execute

## Skill: slack

**Path:** `/usr/lib/node_modules/openclaw/skills/slack/SKILL.md`

### Purpose

Provides structured Slack actions (react, pin/unpin, send, edit, delete messages, fetch member info) via the OpenClaw Slack plugin tool. Uses the bot token configured for OpenClaw.

### Tools Used

- **message** — the `slack` channel plugin (`action` field routes to specific operations)

### Capabilities

- React to a message with a Unicode or `:name:` emoji
- List reactions on a message
- Send a message to a channel or user
- Edit an existing message (by channelId + messageId)
- Delete a message
- Read recent messages from a channel
- Pin / unpin a message
- List pinned items in a channel
- Fetch member info by user ID
- List custom emoji

### Requirements

- OpenClaw Slack plugin configured with a bot token
- Requires `channels.slack` config in OpenClaw config
- Input fields needed: `channelId`, `messageId` (Slack timestamp), `emoji`, `to` target (`channel:<id>` or `user:<id>`), `content`

### Output

- Confirmation of action (send, edit, delete, pin/unpin)
- Listed data (reactions, messages, pins, member info, emoji list) returned as structured JSON via the tool result

## Skill: spotify-player

**Path:** `/usr/lib/node_modules/openclaw/skills/spotify-player/SKILL.md`

### Purpose

Terminal-based Spotify playback and search via `spogo` (preferred) or `spotify_player`. Provides CLI commands for searching tracks, controlling playback, managing devices, and viewing status.

### Tools Used

- **exec** — runs `spogo` or `spotify_player` CLI binaries

### Capabilities

- Search tracks, albums, artists, playlists
- Playback control: play, pause, next, previous
- Device management: list available devices, set active device
- Status display (currently playing)
- Like/unlike tracks (spotify_player fallback)
- Spotify Connect integration via config (`~/.config/spotify-player/app.toml`)
- TUI interface with `?` shortcut help

### Requirements

- Spotify Premium account required
- Either `spogo` (preferred, steipete/tap homebrew) or `spotify_player` (homebrew) installed
- Browser cookie import for auth: `spogo auth import --browser chrome`
- OS: darwin, linux, win32

### Output

- Text output from CLI commands (track info, playback status, search results)
- Exit codes indicate success/failure

## Skill: sql-toolkit

**Path:** `/usr/lib/node_modules/openclaw/skills/sql-toolkit/SKILL.md`

### Purpose

Comprehensive SQL database toolbelt covering SQLite, PostgreSQL, and MySQL. Handles schema design, query writing, migration scripting, index optimization, backup/restore, and performance debugging — no ORM required.

### Tools Used

- **exec** — runs `sqlite3`, `psql`, `mysql` CLIs directly with SQL commands or script files
- Required bins (any one): `sqlite3`, `psql`, `mysql`

### Capabilities

- **SQLite**: zero-setup local databases, CSV import/export, schema inspection, WAL mode for concurrency
- **PostgreSQL**: UUID primary keys, auto-update triggers, enum types, JSONB querying, partial indexes, GIN indexes, window functions, CTEs (including recursive), EXPLAIN ANALYZE for query optimization, pg_dump/pg_restore
- **MySQL**: Auto-increment, InnoDB engine, utf8mb4 charset, JSON type, JSON_EXTRACT shorthand
- **Joins**: inner, left, self-join patterns
- **Aggregations**: group by/having, running totals, rank, moving average
- **Migrations**: numbered SQL file convention with tracking table, rollback conventions
- **Query optimization**: EXPLAIN analysis, composite/covering/partial indexes, unused index detection
- **Backup/restore**: pg_dump (custom/SQL), mysqldump, sqlite .backup/.dump

### Requirements

- One of: `sqlite3`, `psql` (PostgreSQL client), or `mysql` (MySQL client) installed
- OS: linux, darwin, win32
- No external services required (SQLite is zero-setup; psql/mysql require their respective server)

### Output

- Structured query results printed to stdout
- CSV exports written to file
- Backup files written to disk

## Skill: stock-analysis

**Path:** `/usr/lib/node_modules/openclaw/skills/stock-analysis/SKILL.md`

### Purpose

Full-featured stock and cryptocurrency analysis using Yahoo Finance data. Supports portfolio management, watchlists with price/signal alerts, dividend analysis, an 8-dimension scoring system, and two scanner modes (Hot Scanner for viral trends, Rumor Scanner for early signals).

### Tools Used

- **exec** — runs Python scripts via `uv run`: `analyze_stock.py`, `dividends.py`, `watchlist.py`, `portfolio.py`, `hot_scanner.py`, `rumor_scanner.py`
- Required bins: `uv`

### Capabilities

- **Stock analysis**: 8-dimension scoring (earnings surprise 30%, fundamentals 20%, analyst sentiment 20%, sector 15%, momentum 15%, historical 10%, market context 10%, sentiment 10%)
- **Crypto analysis**: 3-dimension (market cap/category, BTC correlation, momentum)
- **Dividend analysis**: yield, payout ratio, 5-year CAGR, consecutive growth years, safety score
- **Watchlists**: add with price target and/or stop loss, alert on signal changes, check triggered alerts
- **Portfolio management**: create portfolios, add assets with quantity/cost, show summary with period returns
- **Hot Scanner**: multi-source trending detection (CoinGecko, Google News, Yahoo Finance, Twitter/X via bird CLI)
- **Rumor Scanner**: M&A rumors, insider activity, analyst upgrades/downgrades, SEC filings, Twitter whispers — with impact scoring (1-10)
- Risk detection: pre-earnings, post-spike, overbought, risk-off, geopolitical, breaking news
- Performance flags: `--fast`, `--no-insider` for faster runs

### Requirements

- `uv` binary installed (homebrew)
- Optional: `bird` npm package for Twitter/X sentiment in Hot Scanner
- Optional: `.env` with `AUTH_TOKEN` and `CT0` for Twitter auth
- Network access for Yahoo Finance, CoinGecko, Google News, SEC EDGAR, Twitter/X
- Data stored at `~/.clawdbot/skills/stock-analysis/` (portfolios.json, watchlist.json)

### Output

- Structured analysis text (default) or JSON (`--output json`) from CLI scripts
- Watchlist alerts in Telegram format with `--notify`
- Hot Scanner and Rumor Scanner support JSON output for automation

## Skill: sudoku

**Path:** `/usr/lib/node_modules/openclaw/skills/sudoku/SKILL.md`

### Purpose

Fetches Sudoku puzzles from `sudokuonline.io`, stores them as JSON in the workspace, renders them as printable PDFs or images on demand, and reveals solutions (full puzzle, single cell, or 3x3 box). Also generates share links in SudokuPad or SCL format.

### Tools Used

- `**exec`** — runs `sudoku.py` scripts (`get`, `render`, `reveal`, `share` subcommands); invokes `python3` with bundled scripts
- `**write`** — likely used to save rendered outputs (PDF/PNG) to workspace
- `**read`** — reads `references/DATA_FORMAT.md` for JSON schema reference

### Capabilities

- Fetch puzzles by type: `kids4n`, `kids4l`, `kids6`, `kids6l`, `easy9`, `medium9`, `hard9`, `evil9`
- Fetch single or multiple puzzles (`--count N`) in one call; auto-batches until enough unseen puzzles are collected
- Target specific source puzzles by partial UUID (`--id <fragment>`)
- Render puzzles as PDF (A4, for printing), PNG (clean image), or minimal HTML
- Reveal solutions as PDF, PNG, or image; reveal individual cells (`--cell r c`) or specific 3x3 boxes (`--box N`)
- Generate share links (SudokuPad or SCL format)
- Format Telegram links as button-style markdown with hidden full URL

### Requirements

- **Binary:** `python3`
- **Python libraries:** `requests`, `Pillow`, `lzstring` (install via `pip install`)
- **Scripts location:** `skills/sudoku/scripts/sudoku.py`

### Output

- **JSON** (default for `get`) — structured puzzle data stored in workspace
- **PDF / PNG / HTML** — via `render` and `reveal` subcommands
- **Plain text** — via `--text` flag on `get`
- **Markdown link** — for Telegram-formatted share links

## Skill: summarize

**Path:** `/usr/lib/node_modules/openclaw/skills/summarize/SKILL.md`

### Purpose

Fast CLI tool to summarize or transcribe URLs, local files (including PDFs), and YouTube/video links. Used on-demand for "summarize this URL/article", "what's this link about?", or "transcribe this YouTube/video" requests. Supports multiple AI model providers and optional services for blocked sites and YouTube fallback.

### Tools Used

- `**exec`** — runs `summarize` CLI with various flags; primary tool
- `**web_fetch`** (indirectly via `--firecrawl`) — content extraction for blocked sites
- `**pdf`** (indirectly via file path support) — PDF summarization

### Capabilities

- Summarize URLs, YouTube links, local files, and PDFs via CLI
- Best-effort transcript extraction from YouTube (`--youtube auto --extract-only`) without needing `yt-dlp`
- `--extract-only` mode for raw content pull (URLs only)
- Configurable model via `--model` flag (default: `google/gemini-3-flash-preview`)
- Output length control: `short|medium|long|xl|xxl|<chars>` or `--max-output-tokens`
- Machine-readable `--json` output
- Firecrawl fallback for blocked sites
- Apify fallback for YouTube if `APIFY_API_TOKEN` is set
- Config file support: `~/.summarize/config.json`
- Conditional transcript expansion (if huge, return tight summary first, then offer section drill-down)

### Requirements

- **Binary:** `summarize` (install via `brew install steipete/tap/summarize`)
- **API keys** (one of): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `GEMINI_API_KEY` (aliases: `GOOGLE_GENERATIVE_AI_API_KEY`, `GOOGLE_API_KEY`)
- **Optional:** `FIRECRAWL_API_KEY` (blocked site fallback), `APIFY_API_TOKEN` (YouTube fallback)

### Output

- **CLI text** (default) — human-readable summary or transcript
- **JSON** (`--json` flag) — machine-readable structured output

## Skill: taskflow

**Path:** `/usr/lib/node_modules/openclaw/skills/taskflow/SKILL.md`

### Purpose

Coordinates multi-step detached tasks as one durable TaskFlow job with owner context, state, waits, and child tasks. Used when a job needs to outlive one prompt or detached run, while keeping one owner session, one return context, and one place to inspect or resume the work. Provides managed flows for plugin/tool orchestration that survive agent restarts and revision conflicts.

### Tools Used

- `**api.runtime.tasks.flow`** (plugin/runtime API) — canonical entrypoint: `api.runtime.tasks.flow.fromToolContext(ctx)` or `api.runtime.tasks.flow.bindSession(...)`
- **No shell exec** — purely an in-process API skill

### Capabilities

- Create managed TaskFlows (`createManaged`) with controller ID, goal, current step, and initial state
- Run linked child tasks (`runTask`) that attach to the flow
- Set flow to `waiting` state (`setWaiting`) when awaiting human reply or external system
- Resume flow (`resume`) when classification or input completes
- Finish (`finish`) or fail (`fail`) a flow
- Cancel entire job (`requestCancel`, `cancel`) including active linked child tasks
- Persist minimum state in `stateJson` for safe resume
- Structured wait metadata via `waitJson` (e.g., `kind`, `channel`, `threadKey`)
- Compact health view via `getTaskSummary(flowId)`
- Revision-checked mutations to prevent conflicting updates
- Human-readable `blockedSummary` for wait reasons

### Requirements

- **Runtime context:** must be called from within OpenClaw plugin/tool context with `sessionKey`
- **Binding method:** `api.runtime.tasks.flow.fromToolContext(ctx)` (trusted context) or `api.runtime.tasks.flow.bindSession({ sessionKey, requesterOrigin })` (pre-resolved binding)

### Output

- Flow objects with properties: `flowId`, `revision`, `stateJson`, `currentStep`, `waitJson`
- `created` / `applied` boolean flags on mutations indicating success
- `reason` / `code` strings for error conditions
- Task summaries with `status`, `startedAt`, `lastEventAt`

## Skill: taskflow-inbox-triage

**Path:** `/usr/lib/node_modules/openclaw/skills/taskflow-inbox-triage/SKILL.md`

### Purpose

Concrete example TaskFlow pattern demonstrating inbox triage, intent routing, waiting on replies (e.g., Slack), and end-of-day summaries. Shows how to wire up `taskflow` for a real-world routing workflow: business items go to Slack and wait, personal items trigger immediate owner notification, everything else accumulated for a daily digest. Serves as a reference implementation alongside the abstract `taskflow` skill.

### Tools Used

- `**api.runtime.tasks.flow`** — same plugin/runtime API as the parent `taskflow` skill: `createManaged`, `runTask`, `setWaiting`, `resume`, `finish`
- `**exec`** / `**message`** — not called directly by the skill, but implied for Slack notifications and subagent dispatch
- **No shell tools** — purely an in-process API reference pattern

### Capabilities

- One owner flow per inbox batch
- Single detached subagent task for classification
- Routing state persisted in `stateJson` with three buckets: `businessThreads[]`, `personalItems[]`, `eodSummary[]`
- `waiting` state while awaiting external replies (e.g., Slack thread)
- Resume when classification or human input completes
- Full flow lifecycle: create → classify → wait → route → finish

### Requirements

- Same runtime context requirements as `taskflow` skill
- Example `stateJson` shape must be followed for consistency
- Example `waitJson` shape for Slack reply blocking (`kind: "reply"`, `channel: "slack"`, `threadKey`)

### Output

- Flow with structured `stateJson` and `waitJson` reflecting the three routing buckets
- Child task linked to parent flow ID
- Final `stateJson` contains all routed items ready for downstream processing

## Skill: ui-ux-pro-max

**Path:** `/usr/lib/node_modules/openclaw/skills/ui-ux-pro-max/SKILL.md`

### Purpose

UI/UX design intelligence and implementation guidance for building polished interfaces. Covers the full design-to-code pipeline: design ideation, UX flow mapping, design system/token creation, component specifications, accessibility reviews, and code generation/refinement for frontend stacks.

### Tools Used

- `**read`** — reads bundled design intelligence data from `skills/ui-ux-pro-max/assets/data/` and upstream references
- `**exec`** — runs the bundled design system generator script: `python3 skills/ui-ux-pro-max/scripts/design_system.py --help`
- `**write`** / `**edit`** — for producing design deliverables, implementation plans, and code changes

### Capabilities

- UI concept + layout: visual direction, grid, typography, color system, key screens/sections
- UX flow mapping: user journeys, critical paths, error/empty/loading states, edge cases
- Design system creation: tokens (color/typography/spacing/radius/shadow), component rules, accessibility notes
- Implementation plans: exact file-level edits, component breakdown, acceptance criteria
- Four-step workflow: triage → produce deliverables → use bundled assets → optional script for tokens
- Design system token generator script (ASCII-friendly structured output)
- Coverage of empty/loading/error states, keyboard navigation, focus states, contrast
- 2-3 font pair options per deliverable
- Supports platforms: web, iOS, Android, desktop
- Supports stacks: React, Next.js, Vue, Svelte, CSS, Tailwind, component libraries

### Requirements

- **Binary:** `python3` (for the design system generator script)
- **Bundled assets:** design data at `skills/ui-ux-pro-max/assets/data/` and upstream refs at `skills/ui-ux-pro-max/references/upstream-skill-content.md`
- **Script:** `skills/ui-ux-pro-max/scripts/design_system.py`

### Output

- Text deliverables: design direction, UX flow documents, implementation plans, component specs
- Code: HTML/CSS/JS, React, Next.js, Vue, Svelte, Tailwind implementations
- Design system tokens: spacing scale, type scale, font pairs, color tokens, component states
- ASCII-friendly structured token output (via script)

## Skill: video-frames

**Path:** `/usr/lib/node_modules/openclaw/skills/video-frames/SKILL.md`

### Purpose

Extracts individual frames from video files using FFmpeg. Used to grab a representative frame for inspection, thumbnail generation, or UI frame extraction from video content.

### Tools Used

- `**exec`** — runs `{baseDir}/scripts/frame.sh` wrapper script (which internally calls `ffmpeg`)
- `**write`** — to save extracted frames to the specified output path

### Capabilities

- Extract first frame from a video as JPEG
- Extract frame at a specific timestamp (`--time 00:00:10`)
- Output as JPEG (`.jpg`) for quick sharing or PNG (`.png`) for crisp UI frames
- Any FFmpeg-supported video format is supported

### Requirements

- **Binary:** `ffmpeg` (install via `brew install ffmpeg`)
- **Script:** `{baseDir}/scripts/frame.sh` (bundled with skill)

### Output

- Image file (JPEG or PNG) written to the specified `--out` path

## Skill: wacli

**Path:** `/usr/lib/node_modules/openclaw/skills/wacli/SKILL.md`

### Purpose

Send third-party WhatsApp messages or sync/search WhatsApp history via the `wacli` CLI. Strictly for contacting people other than the user, or for syncing/searching WhatsApp history on demand. Not for routine user chats (OpenClaw routes those automatically).

### Tools Used

- `**exec`** — runs `wacli` CLI for all operations: `auth`, `sync`, `doctor`, `chats list`, `messages search`, `history backfill`, `send`
- `**message`** — the skill describes message sending workflows but actual delivery goes through `wacli send` CLI

### Capabilities

- **Auth:** QR login + initial sync (`wacli auth`)
- **Sync:** continuous sync (`wacli sync --follow`)
- **Doctor:** check setup health (`wacli doctor`)
- **Find chats:** `wacli chats list --limit N --query "name or number"`
- **Search messages:** `wacli messages search "query" --limit N --chat <jid>`
- **Filtered search:** `--after` / `--before` date filters
- **History backfill:** `wacli history backfill --chat <jid> --requests N --count N`
- **Send text:** `wacli send text --to "+1..." --message "..."`
- **Send to group:** `wacli send text --to "1234567890-123456789@g.us" --message "..."`
- **Send file:** `wacli send file --to "+1..." --file /path/file.pdf --caption "..."`
- JSON output mode (`--json`) for machine-readable results
- Custom store directory (`--store`) override

### Requirements

- **Binary:** `wacli` (install via `brew install steipete/tap/wacli` or `go install github.com/steipete/wacli/cmd/wacli@latest`)
- **Store dir:** `~/.wacli` (overridable with `--store`)
- Phone must be online for backfill operations
- WhatsApp JID format: direct chats `<number>@s.whatsapp.net`, groups `<id>@g.us`

### Output

- Human-readable CLI output (default) or JSON (`--json`)
- Send confirmation via CLI stdout

## Skill: weather

**Path:** `/usr/lib/node_modules/openclaw/skills/weather/SKILL.md`

### Purpose

Retrieves current weather conditions, rain status, temperature, and forecasts for any location worldwide using `wttr.in`. No API key required.

### Tools Used

- `**exec`** — runs `curl` commands against `wttr.in` API endpoints
- No persistent API keys or external services required

### Capabilities

- **Current conditions:** one-liner (`format=3`), detailed (`?0`), or specific city format
- **Forecasts:** 3-day default, week forecast (`format=v2`), specific day (`?0`=today, `?1`=tomorrow, `?2`=day after)
- **Format codes:** `%l` (location), `%c` (condition emoji), `%t` (temperature), `%f` (feels like), `%w` (wind), `%h` (humidity), `%p` (precipitation)
- **Format types:** one-liner, JSON (`format=j1`), PNG image
- **Airport codes:** `curl wttr.in/ORD` for airport-based queries

### Requirements

- **Binary:** `curl` (usually pre-installed on Linux/macOS)
- No API key needed
- Network access to `wttr.in`
- Rate limited — avoid spamming requests

### Output

- **Plain text** (one-liner via `format=3` or composable format string)
- **JSON** (`format=j1`)
- **PNG image** (`wttr.in/London.png`)
- ASCII-compatible output only (default)

## Skill: word-docx

**Path:** `/usr/lib/node_modules/openclaw/skills/word-docx/SKILL.md`

### Purpose

Create, inspect, and edit Microsoft Word documents (`.docx`/`.docm`/`.doc`). Specializes in reliable style handling, numbering, tracked changes, comments, fields, tables, sections, and round-trip compatibility.

### Tools Used

- `**read`** — for reading DOCX package structure (inspecting `word/document.xml`, `styles.xml`, `numbering.xml`, headers, footers)
- `**write`** — for writing DOCX ZIP packages or modifying XML parts inside the package
- `**exec`** (implied) — for invoking conversion tools (e.g., `.doc` to `.docx`), python-docx, or OOXML manipulation libraries
- **OOXML-aware tools** — python-docx or custom XML manipulation (implied by skill scope)

### Capabilities

- Treat `.docx` as OOXML (ZIP of XML parts) for structural reads and edits
- Style-driven generation of new documents (prefer named styles over direct formatting)
- OOXML-aware editing for fragile existing documents (preserving tracked changes, comments, bookmarks, cross-references)
- Lists/numbering system management (`abstractNum`, `num`, paragraph numbering)
- Section-level page layout: margins, orientation, headers, footers, page numbering, section breaks
- Tracked changes workflow: precise edit to changed spans only, minimal replacements over broad rewrites
- Field editing: TOC, page numbers, dates, cross-references, mail merge placeholders
- Comment anchors, review ranges, footnote handling
- Table geometry with explicit widths (avoiding auto-fit drift)
- Round-trip compatibility verification (Word ↔ LibreOffice ↔ Google Docs)
- Legacy `.doc` conversion before modern `.docx` assumptions
- `.docm` (macro-bearing) treated as higher risk

### Requirements

- **Python libraries:** `python-docx` or equivalent OOXML manipulation library (implied)
- **OS support:** Linux, macOS, Windows (`win32`)
- No API keys required
- Related skills installable via `clawhub install <slug>`: `documents`, `brief`, `article`

### Output

- New or edited `.docx`/`.docm` files
- Structured extraction from existing documents (preserving OOXML structure)
- Compatibility reports (round-trip drift identification)
- Style/numbering/layout verification notes

## Skill: obsidian-vault-maintainer

**Path:** `~/.openclaw/plugin-skills/obsidian-vault-maintainer/SKILL.md`

### Purpose

Maintains an Obsidian-friendly memory wiki vault with wikilinks, frontmatter, and official Obsidian CLI awareness. Used when the vault render mode is `obsidian` or the user wants the wiki to interoperate with Obsidian.

### Tools Used

- `**wiki_status`** — confirms vault mode, path, and Obsidian CLI availability (`openclaw wiki status`)
- `**openclaw wiki obsidian status`** — probes official Obsidian CLI availability before use
- `**openclaw wiki obsidian search`** — search within Obsidian vault
- `**openclaw wiki obsidian open`** — open vault/daily note
- `**openclaw wiki obsidian command`** — run arbitrary Obsidian CLI commands
- `**openclaw wiki obsidian daily`** — create/access daily notes via CLI
- `**exec`** (indirect) — for shelling out to `openclaw wiki obsidian-`* helpers

### Capabilities

- Vault mode detection (Obsidian render mode vs. standard)
- Official Obsidian CLI probing before use (does not assume app installed/running/configured)
- Obsidian-aware search, open, command, and daily note operations
- Wikilink conventions: `[[Wikilinks]]`, stable filenames
- Frontmatter that works with Obsidian dashboards and Dataview-style queries
- Deterministic generated sections that don't conflict with handwritten notes
- Safe destructive renames only with a link-repair plan

### Requirements

- **Vault mode:** must be set to `obsidian` for this skill to apply
- **OpenClaw CLI:** `openclaw wiki obsidian-`* subcommands available
- **No external binaries** beyond OpenClaw CLI itself

### Output

- Updates to vault pages with wikilink-compatible content
- Frontmatter-enriched daily notes and pages
- Search results via Obsidian CLI integration

## Skill: wiki-maintainer

**Path:** `~/.openclaw/plugin-skills/wiki-maintainer/SKILL.md`

### Purpose

Maintains the OpenClaw memory wiki vault with deterministic pages, managed blocks, and source-backed updates. Used for all general vault maintenance: page discovery, search, reading, editing, synthesis filing, metadata updates, and linting for contradictions/provenance gaps.

### Tools Used

- `**wiki_status`** — inspect vault mode, path, Obsidian CLI availability
- `**wiki_search`** — discover candidate pages by title, path, ID, or body text (with optional corpus: wiki, memory, or all)
- `**wiki_get`** — inspect exact page content before editing or citing
- `**wiki_apply`** — narrow synthesis filing and metadata updates via tool-level mutation
- `**wiki_lint`** — surface structural issues, contradictions, provenance gaps, and open questions
- `**exec`** — runs `openclaw wiki ingest`, `openclaw wiki compile`, `openclaw wiki lint`, and bridge/unsafe-local import commands
- `**memory_search`** (with `corpus=all`) — recall pass across durable memory plus compiled wiki

### Capabilities

- Vault mode/path inspection
- Page discovery via wiki-specific ranking/provenance
- Controlled ingestion: `openclaw wiki ingest`
- Vault compilation: `openclaw wiki compile`
- Lint runs after meaningful updates
- Bridge mode imports: `openclaw wiki bridge import` for latest public memory artifacts
- Unsafe-local mode imports (`openclaw wiki unsafe-local import`) only when user explicitly opted in
- Managed block markers: generated sections inside managed markers, not overwriting human notes
- Source-backed claims: raw sources and daily notes treated as evidence, not wiki pages as sole source of truth
- Stable page identity: update existing entities over spawning duplicates
- Obsidian-friendly wikilinks preserved when vault mode is `obsidian`

### Requirements

- **Vault mode:** any mode (skill is the general-purpose vault maintenance skill)
- **OpenClaw CLI:** `openclaw wiki` * subcommands
- **Bridge mode:** requires `openclaw wiki bridge import` for shared memory artifacts
- **Unsafe-local mode:** requires explicit user opt-in

### Output

- Lint reports: contradictions, provenance gaps, open questions
- Syntheses and metadata updates applied via `wiki_apply`
- Wiki pages created/updated with deterministic content
- Managed block markers protecting human-written content

