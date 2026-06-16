# PKB Web App (Stage 2) — Design

**Date:** 2026-06-14
**Status:** Approved design (pending spec review). Builds on Plan 1 (data layer + agent core).

The device-native web app that sits on Plan 1's FastAPI backend — the "thin wrapper around AI" from the master spec, now designed in detail. It collapses the friction of the common loops (log into a tile, capture, chat) into one-tap + free-text, and adds desktop-only browsing/grounded-chat.

## Stack & serving

- **Vite + React + TypeScript SPA**, built to static files that **FastAPI serves itself** — one origin, one process on the box, no CORS. Dev runs the Vite dev server proxying `/api/*` to uvicorn.
- Prod: `vite build` → `dist/`; FastAPI mounts it (`/` → SPA, `/api/*` → the existing endpoints). Single process behind Tailscale.
- State/data fetching: lightweight (TanStack Query or equivalent) — fetch hooks over `/api`, optimistic updates for capture/log, polling (or SSE) for live tile updates. No SSR (single-user, private, dynamic data).

## Theme system (themeable dark)

- One dark "world" (the "Dusk/C" direction), but **fully themeable from a single base hue**.
- **Settings → Theme → color wheel** picks the base hue. The palette is **derived** (OKLCH): background + surfaces = the base hue at rising lightness, text = near-white tinted with it, **accent ≈ complementary** hue at high chroma, **secondary** = analogous. All surfaced as CSS custom properties; changing the base re-themes the whole app live.
- **Default base: forest** (deep green → coral accent). User-changeable anytime; persisted (localStorage + a settings record).
- Accessibility: derivation must keep text/!surface contrast ≥ WCAG AA across the hue wheel (clamp lightness/chroma as needed).

## Mobile design

**Home = dynamic tile dashboard.** Ongoing event(s) pinned at the top; below, a grid of tiles. Each tile shows the most relevant info for its subject and updates live.

Tile types:
- **Ongoing activity** (from Plan 1 `list_open_activities`) — e.g. "⏱ Workout · 3 sets logged".
- **Daily goal** — a goal `item`; shows today's progress/target and a done state when met.
- **Requested metric** — a health/quantified metric the user pinned (e.g. Sleep, Steps).
- **Pending approval** — a wiki correction the agent proposes but wants permission for (the propose-confirm trust tier); tap to review/approve/reject.

**Tap a tile → modal** with a free-text input: type to log into that subject (add sets, update a goal). The agent files it and the **tile reacts live** (e.g. logging 25 min against a 20-min goal flips the tile to ✓ done). The modal is the per-subject analog of the global capture box.

**"Type anything" → ephemeral chat.** Tapping the capture bar opens an ephemeral chat **sheet from the bottom (~⅔ height)**. The agent's **tool/source use is shown inline** (chips: `🔧 update_event`, `🔍 query`, `📄 read <page>`) like prominent chat apps. **Drag the handle up** → full screen, and the chat **becomes persistent**. Saved chats are reachable later via the **`☰` top-left** → a chat **sidebar drawer**. Ephemeral chats that aren't expanded are discarded.

## Desktop design

Desktop is **not** a stretched phone — it has its own shell **and extra capabilities**.

- **Shell (Option A):** a left **icon rail** (Home / Wiki / Data / Settings); the tile dashboard fills the main area (more columns); chat **docks on the right** and expands to full width. Chat history lives behind the rail.
- **Wiki browser (desktop-only):** browse and read wiki pages directly (rendered markdown + frontmatter + links + the index/catalog). Read-only rendering; edits still go through the agent.
- **Integration data views (desktop-only, `📊` tab):** direct views of integration data (Apple Health, Linear). See scope below.
- **Context-aware chat (the desktop superpower):** the right-dock chat **auto-includes whatever you're viewing** as a context chip (a wiki page, a metric view). Asking "why is it like this?" is grounded — the agent knows the referent. The chip is clearable/pinnable; navigating updates it. Implemented by the SPA passing a `context` hint (e.g. `{type: "wiki_page", path}`) to the chat call, which the agent resolves (reads the page / scopes the query).

## Backend additions required (extending Plan 1)

The SPA needs a few endpoints beyond Plan 1's `/capture`, `/activities/open`, `/items`:
- **Tiles feed** — `GET /api/home` returning the ordered tile set (ongoing activities, goal items, pinned metrics, pending approvals) so the home renders in one call.
- **Wiki read** — `GET /api/wiki/index` (catalog) and `GET /api/wiki/page?path=…` (frontmatter + rendered markdown). Reuses `wiki.read_page`; path-containment already enforced.
- **Context-aware chat** — extend the capture/chat call to accept an optional `context` ({type, ref}); the agent incorporates it (reads the page or scopes the query) before responding. Chat sessions: persist messages so persistent chats + the sidebar work (`/api/chats`, `/api/chats/{id}`), including the tool-use events for inline display.
- **Approvals** — a minimal pending-changes mechanism: the agent can enqueue a proposed wiki change instead of auto-filing it; `GET /api/approvals`, `POST /api/approvals/{id}` (approve/reject) → agent applies or discards. Realizes the propose-confirm trust tier the master spec describes.
- **Live updates** — polling first (simple), with an SSE endpoint as an optional upgrade so tiles/chat update without manual refresh.
- **Static hosting** — FastAPI serves the built SPA.

## Scope — real now vs. enriched by later add-ons

This stage builds the **whole web app shell + tile/chat/wiki/theme systems**, wired to what exists, with clearly-marked seams for future data:
- **Live now:** theme engine + settings wheel; tile dashboard framework; ongoing-activity tiles; goal tiles from existing `item`s; tile→modal logging with live reaction; capture; ephemeral + persistent chat with tool-use display + sidebar; conversational query; desktop shell; wiki browser; context-aware chat plumbing; approvals UI + minimal backend.
- **Framework now, data later (seams):**
  - **Metric tiles + `📊` integration views** need **Apple Health / Linear** (roadmap add-ons #3, #8). Plan 2 builds the tile type, the `📊` tab, and the context plumbing; real data lands with those add-ons. Until then these render an empty/"connect…" state.
  - **Daily-objective selection** (which goals surface as "today", scored by time/recency) is the **objective-scheduling engine** (add-on #4). Plan 2 shows goal tiles from existing items and basic per-day targets; the smart daily selection enriches them later.

## Out of scope
- Offline capture queue (nice-to-have; revisit after the core ships).
- Native/PWA packaging (the responsive web app over Tailscale is enough for now).
- The integrations themselves (Apple Health, Linear) — their own roadmap items.

## Likely build decomposition (for writing-plans)

This sub-project is large; it will likely become a short sequence of plans rather than one:
1. **Backend API extensions + SPA scaffold + theme engine** (FastAPI static hosting, `/api/home`, wiki read, chat sessions + context param, approvals; Vite/React app shell; OKLCH theme + settings wheel).
2. **Mobile core** (tile dashboard, tile→modal logging w/ live reaction, capture, ephemeral→persistent chat with tool-use display + sidebar).
3. **Desktop shell + wiki browser + context-aware chat** (rail, right chat dock, wiki render, `📊` stub, context chip).

writing-plans will finalize the split and the per-task detail.

## Open items for planning
- Live updates: start with polling vs. invest in SSE immediately.
- Chat persistence storage (reuse SQLite `events`/a `chats` table vs. markdown) and how tool-use steps are recorded for replay.
- Exact `context` hint schema and how the agent consumes it (system message vs. tool).
- Approvals storage (new table vs. `events` with a `proposed_change` kind) and how the agent decides to propose vs. auto-file.
- Component/library choices (data fetching, color/OKLCH lib, markdown renderer).
