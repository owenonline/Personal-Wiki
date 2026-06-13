# Personal Knowledge Base — Design

**Date:** 2026-06-12
**Status:** Approved (architecture + decomposition). MVP to be planned next.

Inspired by Karpathy's "LLM Wiki" pattern (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): an LLM incrementally builds and maintains a persistent, interlinked markdown wiki rather than re-deriving knowledge via RAG on every query. This system adopts that core and extends it into a daily-driver personal system with structured logging, health correlation, a low-friction capture UI, and scheduled agents.

## Core idea

The wiki is a persistent, compounding artifact the agent maintains; the human curates, directs, and asks questions. We extend Karpathy's prose-only pattern with a parallel **structured store** so quantitative/log/time-series data (workouts, activities, health) is queryable, and a **device-native web app** whose entire job is to collapse the friction of capture and interaction — an AI wrapper tuned so common loops (log a set, start an activity, check objectives) take one tap and free text, not a chat negotiation.

## Goals & principles

- **Auto-filing:** enter free text, it lands in the right place (markdown and/or structured) automatically.
- **Open, morphing schema:** any category can morph into any other (skill→hobby, toy→work project, goal→subgoals) without migrations. Relationships and types are data, not schema.
- **Nothing gets lost:** every change is an atomic git commit; full history; lossless undo.
- **Reuse over reinvention:** markdown + git + Obsidian + Claude Agent SDK + MCPs; build custom only where it removes real friction.
- **Reorganize only when needed:** the agent restructures when interaction demands it, not preemptively.

## Architecture — topology

One **always-on Linux box** runs everything; phone and laptop are web clients. Obsidian is an optional power-user view of the same markdown.

```
                    ALWAYS-ON LINUX BOX
  ┌───────────────────────────────────────────────────────┐
  │  Web server (API + responsive UI)                       │
  │     ├── desktop layout   ┐ same data, device-native     │
  │     └── mobile layout    ┘ (no side-scroll / no stretch)│
  │                                                          │
  │  Agent service (Claude Agent SDK, long-running)          │
  │     ├── LIVE mode: chat, query, conversational capture   │
  │     └── BACKGROUND jobs (cron): inbox drain, weekly       │
  │         review, lint, daily-objective generation, sync    │
  │                                                          │
  │  Data layer (one git repo)                               │
  │     ├── wiki/        markdown prose (Obsidian-compatible) │
  │     ├── data.sqlite  items, events, metrics, event_kinds  │
  │     ├── inbox/       raw captures awaiting filing         │
  │     ├── index.md / log.md                                │
  │     └── SCHEMA.md    the agent's filing conventions       │
  │                                                          │
  │  Connectors: Linear (MCP), Apple Health import, search    │
  └───────────────────────────────────────────────────────┘
        ▲                         ▲                    ▲
     phone (web)            laptop (web)        Obsidian (optional)
```

All intelligence lives in the agent service. The web app is a thin wrapper: fast device-native capture/viewing and shuttling text to/from the agent.

## Data layer

**Rule:** markdown holds open, morphable *knowledge*; SQLite holds only what must be queried as *quantities, time-series, or a schedule*. SQLite is deliberately minimal and generic so the morphing principle needs no migrations.

**Markdown wiki (Obsidian-native, fully open):** concept/entity pages, project notes, goal/skill plans, journal entries, "expand later" lists, ingested-source summaries. Morphing = move/relabel/re-link a page; git keeps history.

**SQLite — generic tables (not a domain schema):**

```
items     id, type, title, status, wiki_path, parent_id,
          estimated_minutes, last_active_at, attrs(JSON)
          -- goals/projects/skills/hobbies/lists are ALL "items".
          -- morphing = UPDATE type (one field), no migration.
          -- splitting a goal = new rows w/ parent_id. powers home screen.

events    id, ts, kind, item_id?, location, payload(JSON), wiki_path?
          -- append-only: activity start/stop/updates, workout sets,
          -- "filed this capture". the activity + workout log.
          -- ONE ROW PER ATOMIC FACT (one row per set), flat payload.

metrics   ts, source, name, value, unit
          -- generic time-series: Apple Health sleep/HR/steps, etc.
          -- what health-correlation queries run against.

event_kinds  kind, field, type, unit, description   (the schema registry)
```

**Schema registry (`event_kinds`) — the load-bearing piece.** A self-describing registry the agent maintains and **reads before every file and every query**. When the user logs something new, the agent extends the registry (new kind/field) and git-commits it. Before querying, the agent reads the registry so it knows exactly what shapes exist. This is the consistency anchor that makes the evolving schema both *open* and *reliably retrievable* — Claude's NL→struct and struct→SQL abilities are necessary but not sufficient without it. SQLite native JSON (`json_extract`) handles querying; hot paths (e.g. workouts) earn generated-column indexes later — an optimization, not a schema change.

**Linking & coherence:**
- `events.item_id → items.id → items.wiki_path ↔` markdown frontmatter `id` (structured↔markdown bridge, 1:1 for now).
- The agent populates `item_id` at filing time (decides which goal a workout advances).
- Two link systems coexist: Obsidian `[[wikilinks]]` for knowledge browsing; SQLite `item_id` for correlation. `items.wiki_path` bridges them.
- **Single writer:** the agent service is the only writer to wiki + SQLite — no races, no drift.
- The **web app never writes directly:** it reads SQLite for fast views; to write it calls the agent (LIVE for instant inserts, or drops to `inbox/` for heavy filing).
- Each filing op = structured row(s) + prose edit + **one atomic git commit** (the unit of consistency).
- A background lint/reconcile job catches drift (post-MVP add-on #1).

## Agent — modes & routing

Single entry point; the agent classifies and routes:

```
your text ──► agent classifies ──┬─► bounded structured op?  -> LIVE (do it now, return card)
                                  ├─► live question/query?    -> LIVE (search, answer, cite)
                                  └─► heavy knowledge dump?   -> queue to inbox, ack now,
                                                                 BACKGROUND filing + receipt
```

- **LIVE** (synchronous, bounded): start/stop activity, log sets, log a metric, conversational queries.
- **BACKGROUND** (cron/queue, no waiting): heavy multi-page ingests, daily objective generation, weekly review, lint/reconcile, external sync.
- Rule: waiting + bounded → LIVE; heavy or scheduled → BACKGROUND. Heavy dumps get an instant "got it, filing this" ack.

## Trust model — three tiers by reversibility

1. **Structured inserts** (sets, activities, metrics): auto-file instantly, show a glanceable **tap-to-correct card**. High trust; trivially reversible.
2. **Knowledge filing** (notes, ingests): auto-filed in background, then a **receipt** in the feed ("created X, updated Y, Z") with links.
3. **Destructive / ambiguous / cross-cutting** (merge pages, morph a goal's type, delete): agent **proposes, you confirm.**

- **Undo is git-backed:** every filing = one atomic commit, so undo = revert. Lossless.
- **Corrections teach the system:** fixing a parse updates the registry / `SCHEMA.md` conventions (e.g. "'x5x2' = 5 reps × 2 sets"), improving consistency over time.

## Hero flow — activity/workout logging (end to end)

1. "I'm starting a workout" → agent (LIVE) inserts `events{kind:workout_session, payload:{status:in_progress}}` → home page shows an in-progress card.
2. Tap the card, type "bench 135x5x2, 155x3, feeling sluggish" → agent parses → inserts `workout_set` rows + a `mood` row against the session, extending the registry if needed → tap-to-correct card shows the parse.
3. "Done" → session row → `status:done`, `end_ts`.
4. Weeks later: "sluggish workouts vs. sleep?" → agent reads registry → joins `mood.valence<0` sessions against `metrics` sleep series → answers, can file the finding back as a wiki page.

## MVP — "the spine" (one milestone, likely several PRs)

Goal: type free text on your phone, watch it get filed correctly, ask about it later.

- **Box + repo skeleton:** git repo with `wiki/`, `data.sqlite` (items/events/metrics/event_kinds), `inbox/`, `index.md`, `log.md`, `SCHEMA.md`.
- **Agent service** (Claude Agent SDK): single smart-routing entry point, LIVE + BACKGROUND modes, tools for read/write markdown, query/write SQLite, search, git-commit; registry read/extend/query.
- **Activity/workout logging loop** (hero flow): start activity → live in-progress card → free-text sets/feeling → registry-backed events → tap-to-correct.
- **Knowledge capture (thin):** drop a note/idea → agent files to the right markdown page → receipt with links. (Full multi-page cross-referencing ingest is add-on #2.)
- **Conversational query** over both stores: read, answer, cite. (Filing answers back = later.)
- **Git-backed undo** + the structured/knowledge trust tiers.
- **Responsive web app:** device-native mobile + desktop layouts; home screen = capture box + in-progress activities + recent-filings feed.

**Deliberately NOT in MVP:** objective-scheduling home screen, Apple Health, Linear, weekly reviews, background planners, lint.

## Post-MVP roadmap (each its own spec → plan → PR)

1. **Lint/reconcile job** — contradictions, orphans, store drift. *Integrity first.*
2. **Source ingestion** — Obsidian Web Clipper → full Karpathy-style multi-page ingest. *Completes the core.*
3. **Apple Health import + correlation** — populate `metrics`; "sluggish vs. sleep", "am I burnt out".
4. **Goals/objectives + scheduling home screen** — daily-objective feed scored by est. time / time-since-last-practiced; talk-to-agent to swap tasks.
5. **Weekly review + progress report** — background job + notification; re-adjust lagging goals. *Builds on #4.*
6. **Conversational retrieval of things-to-do** — "bored, what can I do" over goals/projects/lists. *Builds on #4.*
7. **Background planning agent** — "learn X / hit goal Y" → background agent drafts a plan, iterates until finalized. *Builds on #4.*
8. **Linear integration** (personal + engram via MCP) — file project work out, pull status.
9. **`links` edge table** — many-to-many correlation, only if/when needed.

## Cut / deferred

- **"Sim time" (freezing threads for sim-seconds proportional to LLM latency):** cut. It belongs to a simulation/game-loop context and has no role in a personal KB. Revisit only if a concrete need surfaces.
- **`links` edge table:** deferred (roadmap #9); `events.item_id` covers 1:1 correlation until many-to-many bites.

## To resolve during MVP planning

- Web framework / stack for the responsive app and API.
- Exact agent-service process model (long-running daemon, request handling, how LIVE requests are dispatched vs. background cron).
- Search tooling (start with `index.md`; evaluate `qmd` when scale demands).
- Auth for the web app over the internet (it's exposed beyond the LAN).
- `SCHEMA.md` ↔ `event_kinds` table relationship (narrative conventions vs. machine-readable registry) and how they stay in sync.
