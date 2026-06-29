"""Full OpenClaw 67-skill catalog with detailed capabilities, tool tiers,
privacy-relevant metadata, and persona-to-skill matching.

Every generated task must use at least 3-4 skills from this catalog (MINIMUM 3).
"""

from __future__ import annotations

import random
from typing import Any

# ─── Full 67-Skill Catalog ───────────────────────────────────────────────────
# Each skill entry:
#   name          — skill slug (matches openclaw_skills field)
#   tier          — T1 (Local), T2 (1P Cloud), T3 (3P External)
#   category      — functional grouping
#   capability    — one-line capability summary for the LLM prompt
#   tools_used    — what the skill actually calls (exec, browser, etc.)
#   privacy_notes — data-level and consent implications
#   tags          — keyword tags for matching to persona attributes

SKILLS_CATALOG: list[dict[str, Any]] = [
    # ── Health & Wellness ────────────────────────────────────────────────────
    {
        "name": "health",
        "tier": "T1",
        "category": "Health",
        "capability": "Personalized wellness guidance — nutrition, sleep, fitness, mental health; never diagnoses or prescribes",
        "tools_used": ["(advisory only)"],
        "privacy_notes": "L3 health data discussed verbally; no storage",
        "tags": ["health", "fitness", "nutrition", "wellness", "medical", "mental_health"],
    },
    {
        "name": "plan2meal",
        "tier": "T1",
        "category": "Health",
        "capability": "Manage recipes and grocery lists via Plan2Meal — add URLs, search, create grocery lists",
        "tools_used": ["exec"],
        "privacy_notes": "Dietary preferences are L2; allergy data may be L3",
        "tags": ["cooking", "food", "recipe", "meal", "nutrition", "grocery"],
    },
    {
        "name": "healthcheck",
        "tier": "T1",
        "category": "Health",
        "capability": "Audit and harden hosts — SSH, firewall, updates, exposure, cron checks, risk posture",
        "tools_used": ["exec"],
        "privacy_notes": "Reads system state; state-changing actions need user approval",
        "tags": ["security", "audit", "ssh", "firewall", "hardening"],
    },
    # ── Productivity & Task Management ───────────────────────────────────────
    {
        "name": "productivity",
        "tier": "T1",
        "category": "Productivity",
        "capability": "Personal productivity OS — goals, projects, tasks, habits, planning, reviews, inbox triage",
        "tools_used": ["read", "write"],
        "privacy_notes": "Stores in ~/productivity/; local only",
        "tags": ["productivity", "tasks", "habits", "planning", "goals", "gtd"],
    },
    {
        "name": "taskflow",
        "tier": "T1",
        "category": "Productivity",
        "capability": "Multi-step durable task flows with owner context, state, waits, and child tasks",
        "tools_used": ["api.runtime.tasks.flow"],
        "privacy_notes": "State persisted locally; sensitive data in stateJson needs care",
        "tags": ["workflow", "automation", "task_management", "orchestration"],
    },
    {
        "name": "taskflow-inbox-triage",
        "tier": "T3",
        "category": "Productivity",
        "capability": "Email/inbox triage with intent routing, Slack waits, and end-of-day summaries",
        "tools_used": ["api.runtime.tasks.flow"],
        "privacy_notes": "Routes to Slack (T3); L2+ email content needs consent gate; L3+ is hardblock",
        "tags": ["email", "triage", "inbox", "routing", "slack"],
    },
    {
        "name": "self-reflection",
        "tier": "T1",
        "category": "Productivity",
        "capability": "Cron-triggered reflection engine — logs insights, tracks reflection stats over time",
        "tools_used": ["exec"],
        "privacy_notes": "Writes to local memory files only",
        "tags": ["reflection", "journaling", "self_improvement", "memory"],
    },
    {
        "name": "self-improving",
        "tier": "T1",
        "category": "Productivity",
        "capability": "Autonomous learning from corrections — tiered local memory with hot/warm/cold promotion",
        "tools_used": ["read", "write", "edit"],
        "privacy_notes": "All data stays in ~/self-improving/; no network",
        "tags": ["learning", "memory", "self_improvement", "patterns"],
    },
    # ── Documents & Office ───────────────────────────────────────────────────
    {
        "name": "excel-xlsx",
        "tier": "T1",
        "category": "Documents",
        "capability": "Create, inspect, edit Excel workbooks — formulas, styling, charts, date handling, large files",
        "tools_used": ["exec", "write", "read"],
        "privacy_notes": "L3 financial data in spreadsheets; preserve type safety for IDs",
        "tags": ["excel", "spreadsheet", "finance", "data", "budget", "accounting"],
    },
    {
        "name": "word-docx",
        "tier": "T1",
        "category": "Documents",
        "capability": "Create, inspect, edit Word documents — styles, numbering, tracked changes, OOXML-aware",
        "tools_used": ["read", "write", "exec"],
        "privacy_notes": "May contain L2-L4 PII in document content; tracked changes preserve history",
        "tags": ["word", "document", "writing", "report", "letter", "contract"],
    },
    {
        "name": "powerpoint-pptx",
        "tier": "T1",
        "category": "Documents",
        "capability": "Create, inspect, edit PowerPoint decks — layouts, charts, notes, visual QA",
        "tools_used": ["read", "write", "exec", "canvas"],
        "privacy_notes": "Presentations may contain L2 business data, L3 financial projections",
        "tags": ["powerpoint", "presentation", "slides", "deck", "business"],
    },
    {
        "name": "markdown-converter",
        "tier": "T1",
        "category": "Documents",
        "capability": "Convert PDF, Word, Excel, HTML, images, audio, YouTube to Markdown via markitdown",
        "tools_used": ["exec"],
        "privacy_notes": "Source files may contain embedded PII; OCR can extract hidden text",
        "tags": ["conversion", "markdown", "pdf", "document", "ocr"],
    },
    {
        "name": "humanizer",
        "tier": "T1",
        "category": "Documents",
        "capability": "Rewrite AI-generated text to sound natural — detects 24 AI-writing patterns",
        "tools_used": ["read", "write", "edit"],
        "privacy_notes": "Input text may contain PII; output should preserve privacy level",
        "tags": ["writing", "editing", "ai_detection", "natural_language"],
    },
    # ── Data & Research ──────────────────────────────────────────────────────
    {
        "name": "data-analysis",
        "tier": "T1",
        "category": "Data",
        "capability": "SQL, KPI debugging, cohort analysis, funnel analysis, statistical rigor, decision briefs",
        "tools_used": ["exec", "read", "write"],
        "privacy_notes": "Datasets may contain L2-L3 PII; anonymization before output",
        "tags": ["data", "analytics", "sql", "statistics", "kpi", "cohort"],
    },
    {
        "name": "sql-toolkit",
        "tier": "T1",
        "category": "Data",
        "capability": "SQLite/PostgreSQL/MySQL — schema design, queries, migrations, index optimization, backup",
        "tools_used": ["exec"],
        "privacy_notes": "Databases store all data levels; backup files contain raw PII",
        "tags": ["sql", "database", "postgres", "mysql", "sqlite", "query"],
    },
    {
        "name": "code-analysis",
        "tier": "T1",
        "category": "Data",
        "capability": "Analyze Git repos — commit habits, work patterns, code quality, developer scoring, bus factor",
        "tools_used": ["exec"],
        "privacy_notes": "Author names/emails are L2; informed consent required for team repos",
        "tags": ["code_review", "git", "developer", "analysis", "metrics"],
    },
    {
        "name": "academic-research",
        "tier": "T3",
        "category": "Data",
        "capability": "Search 250M+ academic papers via OpenAlex — literature reviews, citations, thematic clustering",
        "tools_used": ["exec"],
        "privacy_notes": "No API key needed; public data only; no PII concerns for search",
        "tags": ["research", "academic", "papers", "literature", "science", "education"],
    },
    # ── Development & DevOps ─────────────────────────────────────────────────
    {
        "name": "code",
        "tier": "T1",
        "category": "Development",
        "capability": "Coding workflow guidance — planning, implementation, verification, testing; stores preferences in ~/code/memory.md",
        "tools_used": ["read", "write", "exec", "browser"],
        "privacy_notes": "User preferences are L1; code may contain embedded secrets (L4)",
        "tags": ["coding", "programming", "development", "software", "debugging"],
    },
    {
        "name": "github",
        "tier": "T3",
        "category": "Development",
        "capability": "GitHub via gh CLI — PRs, issues, CI/workflows, API queries, auth management",
        "tools_used": ["exec"],
        "privacy_notes": "GitHub is T3 (third-party); GH_TOKEN is L4 credential; L2+ data in PRs needs consent gate; L3+ is hardblock",
        "tags": ["git", "github", "version_control", "pr", "ci_cd"],
    },
    {
        "name": "api-dev",
        "tier": "T1",
        "category": "Development",
        "capability": "Scaffold, test, debug REST/GraphQL APIs — curl, OpenAPI specs, mock servers, JWT decode",
        "tools_used": ["exec", "write"],
        "privacy_notes": "API responses may contain L2-L4 PII; JWT tokens contain identity claims",
        "tags": ["api", "rest", "graphql", "testing", "openapi", "jwt"],
    },
    {
        "name": "devops",
        "tier": "T1",
        "category": "Development",
        "capability": "CI/CD, deployment strategies, IaC (Terraform/Ansible), container best practices, secrets management, monitoring",
        "tools_used": ["exec", "write", "read"],
        "privacy_notes": "Secrets management critical; env vars, vault, sealed secrets all L4",
        "tags": ["devops", "ci_cd", "terraform", "ansible", "docker", "kubernetes", "deployment"],
    },
    {
        "name": "docker-essentials",
        "tier": "T1",
        "category": "Development",
        "capability": "Docker container lifecycle — run, build, compose, networking, volumes, multi-stage builds",
        "tools_used": ["exec"],
        "privacy_notes": "Container env vars may contain L4 secrets; image layers can leak data",
        "tags": ["docker", "container", "compose", "devops"],
    },
    {
        "name": "backend-patterns",
        "tier": "T1",
        "category": "Development",
        "capability": "Backend architecture — repository/service patterns, caching, auth middleware, rate limiting, RBAC, logging",
        "tools_used": ["exec", "write", "read"],
        "privacy_notes": "Auth patterns handle L4 credentials; logging must exclude PII",
        "tags": ["backend", "architecture", "node", "express", "nextjs", "patterns"],
    },
    {
        "name": "nextjs-expert",
        "tier": "T1",
        "category": "Development",
        "capability": "Next.js 15 App Router — routing, Server/Client Components, Server Actions, auth, middleware, caching",
        "tools_used": ["(knowledge only)"],
        "privacy_notes": "Auth setup handles L4 session tokens; middleware for route protection",
        "tags": ["nextjs", "react", "frontend", "fullstack", "web"],
    },
    # ── Design & Media ───────────────────────────────────────────────────────
    {
        "name": "frontend-design-3",
        "tier": "T1",
        "category": "Design",
        "capability": "Production-grade frontend with distinctive aesthetics — brutalist, retro-futuristic, luxury, organic",
        "tools_used": ["write", "exec", "canvas"],
        "privacy_notes": "Pure frontend; no PII concerns unless form fields collect it",
        "tags": ["frontend", "design", "ui", "css", "react", "web"],
    },
    {
        "name": "ui-ux-pro-max",
        "tier": "T1",
        "category": "Design",
        "capability": "Full design-to-code pipeline — ideation, UX flows, design tokens, component specs, accessibility",
        "tools_used": ["read", "exec", "write"],
        "privacy_notes": "Design specs may include PII field layouts (forms, profiles)",
        "tags": ["ux", "ui", "design", "accessibility", "wireframe", "prototype"],
    },
    {
        "name": "excalidraw",
        "tier": "T1",
        "category": "Design",
        "capability": "Generate hand-drawn style PNG diagrams — flowcharts, architecture, from Excalidraw JSON",
        "tools_used": ["write", "exec", "canvas"],
        "privacy_notes": "Diagrams may contain system architecture with credential flows",
        "tags": ["diagram", "whiteboard", "sketch", "architecture", "flowchart"],
    },
    {
        "name": "mermaid-diagrams",
        "tier": "T1",
        "category": "Design",
        "capability": "Text-based diagrams — class, sequence, flowchart, ERD, C4, state, git, Gantt; renders in GitHub/VS Code",
        "tools_used": ["(syntax generation)"],
        "privacy_notes": "ERDs may reveal data model with PII field names",
        "tags": ["diagram", "mermaid", "flowchart", "sequence", "erd", "architecture"],
    },
    {
        "name": "ffmpeg-video-editor",
        "tier": "T1",
        "category": "Media",
        "capability": "Video editing via FFmpeg — cut, convert, compress, GIF, subtitles, watermark, speed change",
        "tools_used": ["exec", "write"],
        "privacy_notes": "Videos may contain L2 faces, L3 private conversations, L4 biometrics",
        "tags": ["video", "editing", "ffmpeg", "media", "audio", "conversion"],
    },
    {
        "name": "video-frames",
        "tier": "T1",
        "category": "Media",
        "capability": "Extract individual frames from video files as JPEG/PNG via FFmpeg",
        "tools_used": ["exec", "write"],
        "privacy_notes": "Extracted frames may contain biometric L4 face data",
        "tags": ["video", "frames", "screenshot", "thumbnail"],
    },
    {
        "name": "edge-tts",
        "tier": "T3",
        "category": "Media",
        "capability": "Microsoft Edge neural TTS — dozens of voices, rate/pitch/volume control, subtitle generation",
        "tools_used": ["tts", "exec"],
        "privacy_notes": "Text sent to Microsoft servers; L2+ PII in text gets transmitted to 3P",
        "tags": ["tts", "speech", "voice", "audio", "text_to_speech"],
    },
    {
        "name": "openai-whisper-api",
        "tier": "T3",
        "category": "Media",
        "capability": "Transcribe audio via OpenAI Whisper — multi-language, configurable output",
        "tools_used": ["exec"],
        "privacy_notes": "Audio sent to OpenAI (T3); transcripts may contain L2-L3 spoken PII",
        "tags": ["transcription", "speech_to_text", "audio", "whisper"],
    },
    {
        "name": "openrouter-transcribe",
        "tier": "T3",
        "category": "Media",
        "capability": "Transcribe audio via OpenRouter using Gemini/GPT-4o — wav conversion, base64 encoding",
        "tools_used": ["exec"],
        "privacy_notes": "Audio sent to OpenRouter (T3); same L2-L3 spoken PII risks as whisper",
        "tags": ["transcription", "speech_to_text", "audio", "openrouter"],
    },
    {
        "name": "sherpa-onnx-tts",
        "tier": "T1",
        "category": "Media",
        "capability": "Local offline TTS using sherpa-onnx — no cloud dependency, WAV output",
        "tools_used": ["exec", "write"],
        "privacy_notes": "Fully local; no data transmission; safe for L4 text content",
        "tags": ["tts", "speech", "voice", "offline", "local"],
    },
    # ── Communication & Social ───────────────────────────────────────────────
    {
        "name": "slack",
        "tier": "T3",
        "category": "Communication",
        "capability": "Slack actions — send/read messages, react, pin/unpin, member info, custom emoji",
        "tools_used": ["message"],
        "privacy_notes": "Messages are T3; L2+ content needs consent gate before sending",
        "tags": ["slack", "messaging", "communication", "team", "chat"],
    },
    {
        "name": "wacli",
        "tier": "T3",
        "category": "Communication",
        "capability": "WhatsApp CLI — send text/files, sync history, search messages, backfill conversations",
        "tools_used": ["exec"],
        "privacy_notes": "Messages are T3; phone numbers L2; message content may be L2-L3",
        "tags": ["whatsapp", "messaging", "communication", "mobile"],
    },
    {
        "name": "relationship-skills",
        "tier": "T1",
        "category": "Communication",
        "capability": "Interpersonal guidance — communication frameworks, conflict resolution, date ideas, relationship health",
        "tools_used": ["(advisory only)"],
        "privacy_notes": "Discussion of relationships is L2; specific relationship details may be L3",
        "tags": ["relationships", "communication", "dating", "conflict", "social"],
    },
    # ── Browser & Automation ─────────────────────────────────────────────────
    {
        "name": "browser-automation",
        "tier": "T3",
        "category": "Automation",
        "capability": "Multi-step web automation — login, tab management, stale-ref recovery, Google Meet; uses Playwright refs",
        "tools_used": ["browser"],
        "privacy_notes": "Browser sessions handle L4 credentials (login); page content may contain any PII level",
        "tags": ["browser", "automation", "playwright", "web", "scraping", "login"],
    },
    {
        "name": "desktop-control",
        "tier": "T1",
        "category": "Automation",
        "capability": "Desktop automation — pixel-precise mouse/keyboard control, screenshots, window management, clipboard",
        "tools_used": ["exec"],
        "privacy_notes": "Screenshots may capture L4 credentials on screen; clipboard contains copied PII",
        "tags": ["desktop", "automation", "mouse", "keyboard", "screenshot", "gui"],
    },
    {
        "name": "automation-workflows",
        "tier": "T3",
        "category": "Automation",
        "capability": "No-code automation design (Zapier/Make/n8n) — triggers, conditions, actions, error handling, ROI",
        "tools_used": ["exec", "browser", "write"],
        "privacy_notes": "Workflows route data through T3 services; PII in triggers/actions needs classification",
        "tags": ["automation", "zapier", "make", "n8n", "workflow", "nocode"],
    },
    {
        "name": "agent-team-orchestration",
        "tier": "T1",
        "category": "Automation",
        "capability": "Multi-agent teams — roles, task lifecycle, handoff protocols, quality gates, sub-agent spawning",
        "tools_used": ["sessions_spawn"],
        "privacy_notes": "Sub-agents inherit sensitivity context; handoffs must carry data classification",
        "tags": ["agents", "orchestration", "multi_agent", "delegation", "team"],
    },
    # ── Integrations & APIs ──────────────────────────────────────────────────
    {
        "name": "api-gateway",
        "tier": "T3",
        "category": "Integrations",
        "capability": "Maton-managed routing for 140+ services (Slack, Notion, GitHub, Stripe, Google) — single API key",
        "tools_used": ["exec", "browser"],
        "privacy_notes": "All data routed through Maton (T3); modify ops need user approval; L2+ blocked by default",
        "tags": ["api", "gateway", "integration", "oauth", "maton"],
    },
    {
        "name": "notion",
        "tier": "T3",
        "category": "Integrations",
        "capability": "Notion API — create/query pages, databases, append blocks, update properties, search",
        "tools_used": ["exec"],
        "privacy_notes": "Notion is T3 (third-party); L2+ data needs consent gate; L3+ is hardblock without documented exception",
        "tags": ["notion", "notes", "wiki", "database", "workspace", "knowledge_base"],
    },
    {
        "name": "gog",
        "tier": "T2",
        "category": "Integrations",
        "capability": "Google Workspace CLI — Gmail, Calendar, Drive, Contacts, Sheets, Docs; requires OAuth",
        "tools_used": ["exec", "write", "read"],
        "privacy_notes": "Google services are T2; email content L2-L3; calendar events L2; contacts L2",
        "tags": ["google", "gmail", "calendar", "drive", "sheets", "docs"],
    },
    # ── Finance & Business ───────────────────────────────────────────────────
    {
        "name": "cfo",
        "tier": "T1",
        "category": "Finance",
        "capability": "Financial strategy — planning, cash management, fundraising, board reporting, M&A diligence",
        "tools_used": ["read", "exec"],
        "privacy_notes": "Financial models contain L3 salary, revenue, equity data",
        "tags": ["finance", "cfo", "budget", "fundraising", "cash_flow", "board"],
    },
    {
        "name": "stock-analysis",
        "tier": "T3",
        "category": "Finance",
        "capability": "Stock/crypto analysis — 8-dimension scoring, dividends, watchlists, portfolio, hot scanner, rumor scanner",
        "tools_used": ["exec"],
        "privacy_notes": "Portfolio data is L3 financial; watchlists reveal investment strategy",
        "tags": ["stocks", "investing", "crypto", "portfolio", "trading", "finance"],
    },
    {
        "name": "polymarket",
        "tier": "T3",
        "category": "Finance",
        "capability": "Prediction markets — odds, trending, search, order books, trades, positions",
        "tools_used": ["exec"],
        "privacy_notes": "Wallet/private key is L4; position data is L3 financial",
        "tags": ["prediction", "markets", "polymarket", "trading", "crypto"],
    },
    {
        "name": "marketing-mode",
        "tier": "T1",
        "category": "Business",
        "capability": "140+ marketing tactics, launch frameworks, pricing strategy, SEO, copywriting, CRO, analytics",
        "tools_used": ["(knowledge only)"],
        "privacy_notes": "Marketing analytics may contain L2 user behavior data",
        "tags": ["marketing", "seo", "copywriting", "advertising", "growth", "content"],
    },
    # ── Travel & Lifestyle ───────────────────────────────────────────────────
    {
        "name": "flight-search",
        "tier": "T3",
        "category": "Lifestyle",
        "capability": "CLI flight search via Google Flights — one-way/round-trip, passengers, seat class, price comparison",
        "tools_used": ["exec"],
        "privacy_notes": "Travel plans are L2; scrapes Google Flights (T3, no API key)",
        "tags": ["flights", "travel", "booking", "airline", "trip"],
    },
    {
        "name": "goplaces",
        "tier": "T3",
        "category": "Lifestyle",
        "capability": "Google Places API — text search, place details, geocoding, reviews, location bias",
        "tools_used": ["exec"],
        "privacy_notes": "Location queries may reveal L2 home/work areas; needs GOOGLE_PLACES_API_KEY",
        "tags": ["places", "restaurants", "local", "maps", "directions", "reviews"],
    },
    {
        "name": "weather",
        "tier": "T3",
        "category": "Lifestyle",
        "capability": "Current weather, forecasts, format codes via wttr.in — no API key needed",
        "tools_used": ["exec"],
        "privacy_notes": "Location queries are L1-L2; no auth required",
        "tags": ["weather", "forecast", "temperature", "climate"],
    },
    {
        "name": "mechanic",
        "tier": "T1",
        "category": "Lifestyle",
        "capability": "Vehicle maintenance tracker — mileage, service intervals, VIN decode, recalls, fuel economy, warranties",
        "tools_used": ["exec", "write", "read", "edit"],
        "privacy_notes": "VIN is L2; insurance info L3; vehicle registration L2-L3",
        "tags": ["vehicle", "car", "maintenance", "mechanic", "repair", "automotive"],
    },
    {
        "name": "spotify-player",
        "tier": "T3",
        "category": "Lifestyle",
        "capability": "Terminal Spotify playback — search, play, pause, skip, devices, playlists",
        "tools_used": ["exec"],
        "privacy_notes": "Music preferences are L1-L2; Spotify auth cookie is L4",
        "tags": ["music", "spotify", "playlist", "audio", "streaming"],
    },
    {
        "name": "language-learning",
        "tier": "T1",
        "category": "Lifestyle",
        "capability": "AI language tutor — vocabulary, grammar, conversation, flashcards, script instruction, exam prep",
        "tools_used": ["(conversational)"],
        "privacy_notes": "No PII concerns; purely educational content",
        "tags": ["language", "learning", "vocabulary", "grammar", "education", "tutor"],
    },
    {
        "name": "sudoku",
        "tier": "T1",
        "category": "Lifestyle",
        "capability": "Fetch, render, and solve Sudoku puzzles — PDF/PNG output, share links, multiple difficulty levels",
        "tools_used": ["exec", "write"],
        "privacy_notes": "No PII concerns; recreational content",
        "tags": ["puzzle", "game", "sudoku", "recreation"],
    },
    # ── News & Information ───────────────────────────────────────────────────
    {
        "name": "news-summary",
        "tier": "T3",
        "category": "Information",
        "capability": "Fetch and summarize news from BBC, Reuters, NPR, Al Jazeera RSS — optional voice summary",
        "tools_used": ["exec"],
        "privacy_notes": "Public news; optional TTS uses OpenAI (T3)",
        "tags": ["news", "summary", "rss", "journalism", "briefing"],
    },
    {
        "name": "summarize",
        "tier": "T3",
        "category": "Information",
        "capability": "Summarize URLs, local files, PDFs, YouTube — multi-provider AI, extract-only mode",
        "tools_used": ["exec"],
        "privacy_notes": "Content sent to AI provider (T3) for summarization; may contain embedded PII",
        "tags": ["summary", "url", "pdf", "youtube", "transcription", "extraction"],
    },
    # ── Knowledge & Memory ───────────────────────────────────────────────────
    {
        "name": "session-logs",
        "tier": "T1",
        "category": "Knowledge",
        "capability": "Search and analyze agent session history — filter by date, keyword, cost, tool usage",
        "tools_used": ["exec"],
        "privacy_notes": "Session logs contain all conversation history including L2-L4 PII discussed",
        "tags": ["sessions", "logs", "history", "search", "audit"],
    },
    {
        "name": "obsidian-vault-maintainer",
        "tier": "T1",
        "category": "Knowledge",
        "capability": "Maintain Obsidian-friendly memory wiki — wikilinks, frontmatter, daily notes, vault search",
        "tools_used": ["exec"],
        "privacy_notes": "Vault pages may contain L2-L3 personal notes and linked PII",
        "tags": ["obsidian", "notes", "wiki", "vault", "knowledge_base", "memory"],
    },
    {
        "name": "wiki-maintainer",
        "tier": "T1",
        "category": "Knowledge",
        "capability": "OpenClaw memory wiki — page discovery, search, synthesis, metadata updates, lint for contradictions",
        "tools_used": ["wiki_status", "wiki_search", "wiki_get", "wiki_apply", "wiki_lint", "exec"],
        "privacy_notes": "Wiki pages store synthesized knowledge; may contain derived PII",
        "tags": ["wiki", "memory", "knowledge", "synthesis", "maintenance"],
    },
    {
        "name": "ontology",
        "tier": "T1",
        "category": "Knowledge",
        "capability": "Typed knowledge graph — entities (Person, Project, Task, Event), relations, schema constraints, graph transforms",
        "tools_used": ["exec", "read", "write"],
        "privacy_notes": "Entities may contain Person/Credential L2-L4 data; forbidden raw secrets in Credential type",
        "tags": ["knowledge_graph", "ontology", "entities", "relations", "schema"],
    },
    {
        "name": "hatch-trust",
        "tier": "T1",
        "category": "Knowledge",
        "capability": "HTG reference — data classification, tool tiers, consent protocols; always-active policy skill",
        "tools_used": ["(policy only)"],
        "privacy_notes": "Governs all other tool calls; tier-aware tool selection, sensitivity-aware summarization",
        "tags": ["privacy", "policy", "htg", "compliance", "consent"],
    },
    # ── Skill Management ─────────────────────────────────────────────────────
    {
        "name": "skill-hub",
        "tier": "T3",
        "category": "Skills",
        "capability": "Skill discovery, security vetting, installation management — search 3000+ skills from ClawHub",
        "tools_used": ["exec", "read"],
        "privacy_notes": "Skill vetting checks for prompt injection; network access for search/sync",
        "tags": ["skills", "discovery", "installation", "security", "clawhub"],
    },
    {
        "name": "skill-creator",
        "tier": "T1",
        "category": "Skills",
        "capability": "Create, edit, package OpenClaw skills — init, SKILL.md writing, validation, .skill packaging",
        "tools_used": ["exec", "read", "write"],
        "privacy_notes": "No PII concerns; skill development workflow",
        "tags": ["skills", "development", "packaging", "creation"],
    },
    # ── Voice & Social ───────────────────────────────────────────────────────
    {
        "name": "moltspaces",
        "tier": "T3",
        "category": "Social",
        "capability": "Join audio room spaces on Moltspaces — register, configure voice, prepare persona, launch bot",
        "tools_used": ["exec", "write", "read"],
        "privacy_notes": "Voice is biometric L4; personality config may reveal personal traits (L2)",
        "tags": ["voice", "social", "audio", "rooms", "moltspaces", "bot"],
    },
    # ── Infrastructure & Connectivity ────────────────────────────────────────
    {
        "name": "node-connect",
        "tier": "T1",
        "category": "Infrastructure",
        "capability": "Diagnose OpenClaw node pairing failures — QR codes, routing, auth, connection fixing",
        "tools_used": ["exec"],
        "privacy_notes": "QR setup codes are L4 ephemeral credentials; device pairing involves auth tokens",
        "tags": ["node", "pairing", "connectivity", "troubleshooting", "device"],
    },
    {
        "name": "gh-issues",
        "tier": "T3",
        "category": "Development",
        "capability": "Automatic GitHub issue fixing — fetch, spawn sub-agents, fix, PR, monitor reviews; 6-phase pipeline",
        "tools_used": ["exec", "sessions_spawn", "write", "read"],
        "privacy_notes": "GitHub is T3; GH_TOKEN is L4; L2+ data in issues/PRs needs consent gate; L3+ is hardblock",
        "tags": ["github", "issues", "automation", "pr", "ci_cd", "fix"],
    },
    # ── Google Workspace (T3) ─────────────────────────────────────────────────
    {
        "name": "google-gmail",
        "tier": "T3",
        "category": "Communication",
        "capability": "Send, read, draft, and search emails via Gmail API — compose replies, manage labels, attach files",
        "tools_used": ["api.google.gmail"],
        "privacy_notes": "Gmail is T3 (Google); email bodies may contain L2-L3 PII; L2+ content needs consent gate; L3+ is hardblock before send",
        "tags": ["email", "gmail", "communication", "google", "workspace"],
    },
    {
        "name": "google-docs",
        "tier": "T3",
        "category": "Documents",
        "capability": "Create, edit, read, and share Google Docs — collaborative editing, templates, export to PDF",
        "tools_used": ["api.google.docs"],
        "privacy_notes": "Google Docs is T3; document content stored on Google servers; L2+ PII in docs needs consent gate; L3+ is hardblock",
        "tags": ["documents", "google_docs", "writing", "collaboration", "google", "workspace"],
    },
    {
        "name": "google-sheets",
        "tier": "T3",
        "category": "Data",
        "capability": "Create, edit, and analyze Google Sheets — formulas, charts, pivot tables, data import/export",
        "tools_used": ["api.google.sheets"],
        "privacy_notes": "Google Sheets is T3; spreadsheet data on Google servers; L2+ PII (financial, health logs) needs consent gate; L3+ is hardblock",
        "tags": ["spreadsheet", "google_sheets", "data", "analysis", "google", "workspace"],
    },
    {
        "name": "google-drive",
        "tier": "T3",
        "category": "Storage",
        "capability": "Upload, download, share, and organize files in Google Drive — permissions, folders, search",
        "tools_used": ["api.google.drive"],
        "privacy_notes": "Google Drive is T3; files stored on Google; L2+ PII in uploaded files needs consent gate; L3+ is hardblock; sharing exposes to additional parties",
        "tags": ["storage", "google_drive", "files", "sharing", "cloud", "google", "workspace"],
    },
    {
        "name": "google-calendar",
        "tier": "T3",
        "category": "Productivity",
        "capability": "Create, view, edit, and share calendar events — scheduling, invites, reminders, availability checks",
        "tools_used": ["api.google.calendar"],
        "privacy_notes": "Google Calendar is T3; event details (attendees, locations, descriptions) may contain L2 PII; L3+ medical/legal appointments need consent gate",
        "tags": ["calendar", "scheduling", "google_calendar", "events", "google", "workspace"],
    },
    {
        "name": "google-meet",
        "tier": "T3",
        "category": "Communication",
        "capability": "Schedule and manage Google Meet video calls — create links, invite participants, record meetings",
        "tools_used": ["api.google.meet"],
        "privacy_notes": "Google Meet is T3; meeting recordings contain L3 voice biometrics; attendee lists are L2; recording transcripts may contain L2-L3 PII",
        "tags": ["video", "meeting", "google_meet", "conferencing", "google", "workspace"],
    },
]

# ─── Derived indexes ─────────────────────────────────────────────────────────

TIER_1_SKILLS = [s["name"] for s in SKILLS_CATALOG if s["tier"] == "T1"]
TIER_2_SKILLS = [s["name"] for s in SKILLS_CATALOG if s["tier"] == "T2"]
TIER_3_SKILLS = [s["name"] for s in SKILLS_CATALOG if s["tier"] == "T3"]

_SKILLS_BY_NAME: dict[str, dict] = {s["name"]: s for s in SKILLS_CATALOG}

HEART_DOMAINS: dict[str, list[str]] = {
    "H": ["health", "plan2meal", "healthcheck"],
    "E": ["language-learning", "ffmpeg-video-editor", "excalidraw", "mermaid-diagrams",
          "academic-research", "sudoku", "frontend-design-3", "ui-ux-pro-max",
          "edge-tts", "sherpa-onnx-tts", "video-frames", "moltspaces"],
    "A": ["cfo", "stock-analysis", "polymarket", "data-analysis", "excel-xlsx",
          "marketing-mode", "hatch-trust"],
    "R": ["relationship-skills", "slack", "wacli", "browser-automation"],
    "T": ["productivity", "taskflow", "taskflow-inbox-triage", "automation-workflows",
          "word-docx", "powerpoint-pptx", "notion", "obsidian-vault-maintainer"],
}


# ─── Persona-to-Skill matching ───────────────────────────────────────────────

_STRATUM_SKILLS: dict[str, list[str]] = {
    "S1_developer_researcher": [
        "code", "github", "api-dev", "devops", "docker-essentials", "sql-toolkit",
        "session-logs", "obsidian-vault-maintainer", "backend-patterns", "nextjs-expert",
        "code-analysis", "gh-issues", "agent-team-orchestration", "ontology",
    ],
    "S2_creative_professional": [
        "ffmpeg-video-editor", "excalidraw", "mermaid-diagrams", "edge-tts",
        "humanizer", "markdown-converter", "frontend-design-3", "ui-ux-pro-max",
        "video-frames", "sherpa-onnx-tts", "powerpoint-pptx",
    ],
    "S3_proficient_professional": [
        "excel-xlsx", "word-docx", "powerpoint-pptx", "cfo", "notion",
        "data-analysis", "marketing-mode", "automation-workflows",
        "taskflow-inbox-triage", "gog",
    ],
    "S4_knowledge_worker": [
        "excel-xlsx", "word-docx", "taskflow", "summarize", "notion",
        "productivity", "obsidian-vault-maintainer", "news-summary",
        "markdown-converter", "self-reflection",
    ],
    "S5_general_user": [
        "goplaces", "weather", "plan2meal", "health", "flight-search",
        "productivity", "relationship-skills", "language-learning",
        "spotify-player", "sudoku", "mechanic",
    ],
}

_SECTOR_SKILLS: dict[str, list[str]] = {
    "software_tech": ["code", "github", "api-dev", "devops", "docker-essentials",
                      "nextjs-expert", "sql-toolkit", "backend-patterns",
                      "gh-issues", "code-analysis"],
    "data_analytics": ["data-analysis", "sql-toolkit", "excel-xlsx",
                       "code-analysis", "powerpoint-pptx", "ontology"],
    "finance_legal": ["cfo", "stock-analysis", "excel-xlsx", "polymarket",
                      "data-analysis", "word-docx"],
    "healthcare": ["health", "healthcheck", "plan2meal", "excel-xlsx",
                   "word-docx", "summarize"],
    "education": ["academic-research", "language-learning", "word-docx",
                  "markdown-converter", "summarize", "powerpoint-pptx"],
    "creative_arts": ["ffmpeg-video-editor", "excalidraw", "frontend-design-3",
                      "ui-ux-pro-max", "edge-tts", "video-frames",
                      "sherpa-onnx-tts", "mermaid-diagrams"],
    "marketing_sales": ["marketing-mode", "slack", "notion",
                        "automation-workflows", "browser-automation",
                        "powerpoint-pptx", "gog"],
    "media_journalism": ["news-summary", "summarize", "word-docx",
                         "openai-whisper-api", "humanizer",
                         "ffmpeg-video-editor", "openrouter-transcribe"],
    "nonprofit": ["slack", "notion", "excel-xlsx", "word-docx",
                  "automation-workflows", "gog"],
    "hospitality": ["goplaces", "weather", "plan2meal",
                    "automation-workflows", "flight-search"],
    "engineering": ["code", "mermaid-diagrams", "api-dev", "devops",
                    "excel-xlsx", "docker-essentials", "sql-toolkit"],
    "retail": ["automation-workflows", "excel-xlsx", "slack",
               "marketing-mode", "notion", "goplaces"],
    "general": ["taskflow", "productivity", "excel-xlsx", "word-docx",
                "summarize", "self-reflection"],
}

_HOBBY_SKILL_MAP: dict[str, str] = {
    "cooking": "plan2meal", "food": "plan2meal", "recipe": "plan2meal",
    "baking": "plan2meal", "nutrition": "plan2meal",
    "fitness": "health", "health": "health", "yoga": "health",
    "running": "health", "gym": "health", "workout": "health",
    "meditation": "health", "wellness": "health",
    "music": "spotify-player", "guitar": "spotify-player",
    "piano": "spotify-player", "singing": "spotify-player",
    "travel": "flight-search", "hiking": "goplaces",
    "backpacking": "flight-search", "camping": "goplaces",
    "coding": "code", "programming": "code", "dev": "code",
    "hacking": "code", "open source": "github",
    "photography": "ffmpeg-video-editor", "video": "ffmpeg-video-editor",
    "filmmaking": "ffmpeg-video-editor", "editing": "ffmpeg-video-editor",
    "vlogging": "ffmpeg-video-editor",
    "writing": "word-docx", "journal": "self-reflection",
    "blog": "markdown-converter", "poetry": "word-docx",
    "creative writing": "humanizer",
    "gaming": "desktop-control", "chess": "sudoku",
    "puzzles": "sudoku", "board games": "sudoku",
    "investing": "stock-analysis", "stocks": "stock-analysis",
    "crypto": "polymarket", "trading": "stock-analysis",
    "finance": "cfo", "budgeting": "excel-xlsx",
    "language": "language-learning", "languages": "language-learning",
    "car": "mechanic", "vehicle": "mechanic", "auto": "mechanic",
    "motorcycle": "mechanic", "off-road": "mechanic",
    "drone": "code", "robotics": "code", "electronics": "code",
    "drawing": "excalidraw", "illustration": "excalidraw",
    "design": "frontend-design-3", "ui": "ui-ux-pro-max",
    "diagram": "mermaid-diagrams",
    "research": "academic-research", "science": "academic-research",
    "reading": "summarize", "books": "summarize",
    "news": "news-summary", "current events": "news-summary",
    "productivity": "productivity", "organization": "productivity",
    "meal prep": "plan2meal",
    "home automation": "automation-workflows",
    "smart home": "automation-workflows",
    "podcast": "openai-whisper-api",
    "transcription": "openai-whisper-api",
}

_SOCIAL_SKILLS = {"slack", "wacli"}

_UNIVERSAL_POOL = [
    "taskflow", "weather", "productivity", "summarize",
    "self-reflection", "relationship-skills", "hatch-trust",
    "session-logs", "self-improving",
]


_BATCH4_EXCLUDED = {"notion"}


def get_skills_for_persona(persona: dict, *, enterprise_batch: bool = False, chat_focused: bool = False) -> list[dict]:
    """Select 15-20 relevant skills ensuring every persona gets diverse coverage.

    Returns full skill dicts (not just names) for prompt injection.
    """
    sector = persona.get("occupation_sector", persona.get("_occupation_sector", ""))
    stratum = persona.get("stratum", "")
    platforms = list(persona.get("platform_presence", {}).keys())
    relevant: set[str] = {"browser-automation"}

    for skill in _SECTOR_SKILLS.get(sector, _SECTOR_SKILLS["general"]):
        relevant.add(skill)

    for skill in _STRATUM_SKILLS.get(stratum, []):
        relevant.add(skill)

    hobbies = persona.get("hobbies", {})
    hobby_tags: set[str] = set()
    for category, items in hobbies.items():
        if isinstance(items, list):
            hobby_tags.update(str(i).lower() for i in items)
        elif isinstance(items, str):
            hobby_tags.add(items.lower())
    hobby_tag_str = " ".join(hobby_tags)

    for keyword, skill in _HOBBY_SKILL_MAP.items():
        if keyword in hobby_tag_str:
            relevant.add(skill)

    lifestyle = persona.get("lifestyle", {})
    subs = lifestyle.get("subscriptions", [])
    for sub in subs:
        sub_lower = sub.lower()
        if "spotify" in sub_lower:
            relevant.add("spotify-player")
        if "notion" in sub_lower:
            relevant.add("notion")
        if "github" in sub_lower:
            relevant.add("github")
        if "google" in sub_lower:
            relevant.add("gog")
            relevant.update(["google-gmail", "google-docs", "google-sheets",
                             "google-drive", "google-calendar", "google-meet"])

    if persona.get("_has_dev_credentials"):
        relevant.update(["code", "github", "api-dev", "session-logs",
                         "devops", "docker-essentials"])
    if persona.get("_has_vehicles"):
        relevant.add("mechanic")
    if persona.get("_has_biometrics"):
        relevant.add("moltspaces")

    if not enterprise_batch:
        if "slack" in platforms or any("slack" in p.lower() for p in platforms):
            relevant.add("slack")
        if "whatsapp" in platforms or any("whatsapp" in p.lower() for p in platforms):
            relevant.add("wacli")
    else:
        relevant.discard("slack")
        relevant.discard("wacli")

    for s in random.sample(_UNIVERSAL_POOL, min(4, len(_UNIVERSAL_POOL))):
        relevant.add(s)

    t3_pool = [s for s in TIER_3_SKILLS if s not in _SOCIAL_SKILLS] if enterprise_batch else TIER_3_SKILLS
    t3_sample = random.sample(t3_pool, min(3, len(t3_pool))) if t3_pool else []
    for s in t3_sample:
        relevant.add(s)

    t1_pool = [s for s in TIER_1_SKILLS if s not in relevant]
    if t1_pool:
        for s in random.sample(t1_pool, min(3, len(t1_pool))):
            relevant.add(s)

    # Batch 3+: Google Workspace and api-gateway (Maton) available for ALL personas
    relevant.update(["google-gmail", "google-docs", "google-sheets",
                     "google-drive", "google-calendar", "google-meet",
                     "api-gateway"])

    if chat_focused:
        relevant -= _BATCH4_EXCLUDED
        relevant.add("browser-automation")

    all_names = [s["name"] for s in SKILLS_CATALOG]
    if chat_focused:
        all_names = [n for n in all_names if n not in _BATCH4_EXCLUDED]
    while len(relevant) < 15:
        relevant.add(random.choice(all_names))

    return [s for s in SKILLS_CATALOG if s["name"] in relevant]


def build_skills_prompt_section(skills: list[dict]) -> str:
    """Build the skills section for the user prompt with detailed capabilities and privacy notes.

    Uses rich descriptions from to_riju/skills.md when available.
    """
    try:
        from prompts.skills_rich_loader import get_skill_detail
    except ImportError:
        get_skill_detail = None

    by_tier: dict[str, list[dict]] = {"T1": [], "T2": [], "T3": []}
    for s in skills:
        by_tier.get(s["tier"], by_tier["T3"]).append(s)

    lines = [
        "═══ AVAILABLE OPENCLAW SKILLS (for openclaw_skills field) ═══",
        "Each task MUST use 2-3 skills. Pick skills that create interesting privacy interactions.",
        "",
    ]

    tier_labels = {
        "T1": "LOCAL (Tier 1) — safe for all data levels",
        "T2": "1P CLOUD (Tier 2) — L3+ needs exec-approval",
        "T3": "3P EXTERNAL (Tier 3) — L2+ needs consent gate",
    }

    for tier in ("T1", "T2", "T3"):
        tier_skills = by_tier[tier]
        if not tier_skills:
            continue
        lines.append(f"── {tier_labels[tier]} ──")
        for s in sorted(tier_skills, key=lambda x: x["name"]):
            rich = ""
            if get_skill_detail:
                rich = get_skill_detail(s["name"])
            if rich:
                lines.append(
                    f"  • {s['name']} [{s['category']}]"
                    f"\n    {rich}"
                    f"\n    Privacy: {s['privacy_notes']}"
                )
            else:
                lines.append(
                    f"  • {s['name']} [{s['category']}] — {s['capability']}"
                    f"\n    Privacy: {s['privacy_notes']}"
                )
        lines.append("")

    lines.append(
        "SKILL SELECTION RULES:\n"
        "• Every task MUST list EXACTLY 2 skills in openclaw_skills\n"
        "• Across all 5 tasks, use at LEAST 8 different skills\n"
        "• Pair T1 + T3 skills to create tool-tier resolution scenarios\n"
        "• Match skills to the persona's occupation, hobbies, and life situation\n"
        "• T3 skills in a task MUST trigger exec_approval in expected_privacy_actions"
    )
    return "\n".join(lines)
