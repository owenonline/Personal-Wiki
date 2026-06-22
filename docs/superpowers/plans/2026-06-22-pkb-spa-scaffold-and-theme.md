# PKB SPA Scaffold + Theme Engine (Plan 2b) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Vite + React + TypeScript single-page app that Plan 2c/2d build the UI on — including the themeable dark color engine (OKLCH-derived from a base hue, forest default, settings color wheel), a typed API client against the Plan 2a backend, an SSE hook, and the FastAPI → built-SPA serving wired end to end.

**Architecture:** A new `frontend/` workspace (its own `package.json`, isolated from the Python package). Pure logic (theme derivation, persistence, API client) is unit-tested with Vitest; React pieces use Testing Library + jsdom. The theme is a set of CSS custom properties on `:root` derived from one base hex via OKLCH (`culori`); changing the base re-derives and re-applies live. FastAPI serves the built `frontend/dist` via the `spa_dir` hook added in Plan 2a (Task 9).

**Tech Stack:** Vite 5, React 18, TypeScript 5, Vitest + @testing-library/react + jsdom, `culori` (OKLCH), native `fetch`/`EventSource`. Backend touch is one small `get_settings` change (read `PKB_SPA_DIR`).

---

## File Structure

```
.gitignore                       # MODIFY: ignore frontend/node_modules, frontend/dist
frontend/
  package.json                   # NEW: deps + scripts (dev/build/test)
  tsconfig.json                  # NEW
  vite.config.ts                 # NEW: react plugin + vitest config (jsdom)
  index.html                     # NEW: SPA entry
  src/
    main.tsx                     # NEW: React root, mounts <App/>, applies theme
    App.tsx                      # NEW: shell — theme + home sections (minimal)
    vitest.setup.ts              # NEW: @testing-library/jest-dom
    theme/
      derive.ts                  # NEW: deriveTheme(baseHex) -> ThemeTokens (OKLCH)
      derive.test.ts             # NEW
      theme.ts                   # NEW: DEFAULT_BASE, load/save base, applyTheme/applyBase
      theme.test.ts              # NEW
    api/
      client.ts                  # NEW: typed API fns + subscribeEvents
      client.test.ts             # NEW
    components/
      BaseColorPicker.tsx        # NEW: settings base-hue picker
      BaseColorPicker.test.tsx   # NEW
pkb/config.py                    # MODIFY: get_settings reads PKB_SPA_DIR
tests/test_config_spa.py         # NEW: PKB_SPA_DIR -> settings.spa_dir
```

Each task is TDD and ends in the **merge gate** (same convention as Plans 1/2a). Frontend gate: from `frontend/`, `npm test` (Vitest, non-watch) is green, plus `npm run build` succeeds where the task affects the build. Backend-touching tasks also keep `uv run pytest -v` green. Paste the actual summary line before committing; commit only when green.

**Setup note (run once, in Task 1):** `cd frontend && npm install`. Node 18+ assumed (matches the box). Subagents draft files; the controller runs `npm`/`uv` and commits.

---

### Task 1: Frontend scaffold + Vitest

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/vitest.setup.ts`
- Create: `frontend/src/smoke.test.ts`
- Modify: `.gitignore`

- [ ] **Step 1: Add ignores** — append to `.gitignore`:

```
# Frontend
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 2: Write `frontend/package.json`**

```json
{
  "name": "pkb-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "culori": "^4.0.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.6",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^24.1.0",
    "typescript": "^5.5.3",
    "vite": "^5.3.3",
    "vitest": "^2.0.2"
  }
}
```

- [ ] **Step 3: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Write `frontend/vite.config.ts`**

```ts
/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8787", "/capture": "http://localhost:8787" },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/vitest.setup.ts"],
  },
});
```

- [ ] **Step 5: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>PKB</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write `frontend/src/vitest.setup.ts`**

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 7: Write `frontend/src/App.tsx`** (minimal placeholder; real shell in Task 5)

```tsx
export default function App() {
  return <main>PKB</main>;
}
```

- [ ] **Step 8: Write `frontend/src/main.tsx`**

```tsx
import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 9: Write the smoke test `frontend/src/smoke.test.ts`**

```ts
import { describe, expect, it } from "vitest";

describe("toolchain", () => {
  it("runs vitest", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 10: Install, test, build**

Run: `cd frontend && npm install && npm test && npm run build`
Expected: Vitest `1 passed`; `vite build` writes `frontend/dist/index.html`.

- [ ] **Step 11: Merge gate, then commit**

**Unit-test plan:** Vitest runs (smoke passes); `npm run build` produces `frontend/dist/index.html`.
Gate: `cd frontend && npm test` green; `npm run build` succeeds. Commit only if green.

```bash
git add .gitignore frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html frontend/src
git commit -m "feat(spa): Vite + React + TS scaffold with Vitest"
```

---

### Task 2: Theme derivation (`derive.ts`)

Pure OKLCH derivation: one base hex → a coherent dark palette. Background/surfaces are the base hue at rising lightness with low chroma; text is near-white tinted with the hue; accent is the complementary hue at high chroma; secondary is analogous.

**Files:**
- Create: `frontend/src/theme/derive.ts`, `frontend/src/theme/derive.test.ts`

- [ ] **Step 1: Write the failing tests** — `frontend/src/theme/derive.test.ts`

```ts
import { describe, expect, it } from "vitest";

import { deriveTheme, ThemeTokens } from "./derive";

const HEX = /^#[0-9a-f]{6}$/i;

describe("deriveTheme", () => {
  it("returns all tokens as hex strings", () => {
    const t = deriveTheme("#1f6f4a");
    const keys: (keyof ThemeTokens)[] = [
      "bg", "surface", "surface2", "text", "muted", "accent", "secondary",
    ];
    for (const k of keys) expect(t[k]).toMatch(HEX);
  });

  it("is deterministic", () => {
    expect(deriveTheme("#1f6f4a")).toEqual(deriveTheme("#1f6f4a"));
  });

  it("derives different accents for different base hues", () => {
    expect(deriveTheme("#1f6f4a").accent).not.toBe(deriveTheme("#3a52b0").accent);
  });

  it("keeps background dark and text light", () => {
    // crude luminance proxy: sum of RGB bytes
    const lum = (hex: string) =>
      parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16) + parseInt(hex.slice(5, 7), 16);
    const t = deriveTheme("#1f6f4a");
    expect(lum(t.bg)).toBeLessThan(lum(t.text));
    expect(lum(t.bg)).toBeLessThan(200); // dark
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/theme/derive.test.ts`
Expected: FAIL — cannot resolve `./derive`.

- [ ] **Step 3: Write `frontend/src/theme/derive.ts`**

```ts
import { converter, formatHex } from "culori";

export interface ThemeTokens {
  bg: string;
  surface: string;
  surface2: string;
  text: string;
  muted: string;
  accent: string;
  secondary: string;
}

const toOklch = converter("oklch");

function hex(l: number, c: number, h: number): string {
  return formatHex({ mode: "oklch", l, c, h })!;
}

/** Derive a coherent dark palette from one base hex via OKLCH. */
export function deriveTheme(baseHex: string): ThemeTokens {
  const base = toOklch(baseHex) ?? { mode: "oklch", l: 0.5, c: 0.1, h: 150 };
  const h = base.h ?? 0;
  const baseC = base.c ?? 0.1;
  return {
    bg: hex(0.16, Math.min(baseC, 0.03), h),
    surface: hex(0.22, Math.min(baseC, 0.04), h),
    surface2: hex(0.27, Math.min(baseC, 0.05), h),
    text: hex(0.94, 0.02, h),
    muted: hex(0.68, 0.03, h),
    accent: hex(0.72, 0.15, (h + 180) % 360),
    secondary: hex(0.8, 0.1, (h + 40) % 360),
  };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/theme/derive.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** all 7 tokens are valid hex; deterministic; different base hues yield different accents; bg is dark and darker than text.
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/theme/derive.ts frontend/src/theme/derive.test.ts
git commit -m "feat(spa): OKLCH theme derivation from a base hue"
```

---

### Task 3: Theme application + persistence (`theme.ts`)

**Files:**
- Create: `frontend/src/theme/theme.ts`, `frontend/src/theme/theme.test.ts`

- [ ] **Step 1: Write the failing tests** — `frontend/src/theme/theme.test.ts`

```ts
import { beforeEach, describe, expect, it } from "vitest";

import { applyBase, applyTheme, DEFAULT_BASE, loadBase, saveBase } from "./theme";
import { deriveTheme } from "./derive";

describe("theme persistence", () => {
  beforeEach(() => localStorage.clear());

  it("defaults to the forest base", () => {
    expect(loadBase()).toBe(DEFAULT_BASE);
  });

  it("round-trips a saved base", () => {
    saveBase("#3a52b0");
    expect(loadBase()).toBe("#3a52b0");
  });
});

describe("applyTheme", () => {
  it("sets a CSS custom property per token", () => {
    const root = document.documentElement;
    applyTheme(deriveTheme("#1f6f4a"), root);
    expect(root.style.getPropertyValue("--bg")).toMatch(/^#[0-9a-f]{6}$/i);
    expect(root.style.getPropertyValue("--accent")).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("applyBase derives then applies", () => {
    const root = document.documentElement;
    root.style.removeProperty("--accent");
    applyBase("#3a52b0", root);
    expect(root.style.getPropertyValue("--accent")).toBe(deriveTheme("#3a52b0").accent);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/theme/theme.test.ts`
Expected: FAIL — cannot resolve `./theme`.

- [ ] **Step 3: Write `frontend/src/theme/theme.ts`**

```ts
import { deriveTheme, ThemeTokens } from "./derive";

export const DEFAULT_BASE = "#1f6f4a"; // forest
const STORAGE_KEY = "pkb.baseHex";

export function loadBase(): string {
  return localStorage.getItem(STORAGE_KEY) ?? DEFAULT_BASE;
}

export function saveBase(hex: string): void {
  localStorage.setItem(STORAGE_KEY, hex);
}

export function applyTheme(tokens: ThemeTokens, root: HTMLElement = document.documentElement): void {
  for (const [name, value] of Object.entries(tokens)) {
    root.style.setProperty(`--${name}`, value);
  }
}

export function applyBase(hex: string, root: HTMLElement = document.documentElement): void {
  applyTheme(deriveTheme(hex), root);
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/theme/theme.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `loadBase` defaults to forest; `saveBase`/`loadBase` round-trip via localStorage; `applyTheme` sets a `--token` CSS var per token; `applyBase` derives then applies (accent matches `deriveTheme`).
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/theme/theme.ts frontend/src/theme/theme.test.ts
git commit -m "feat(spa): theme apply + base-hue persistence (forest default)"
```

---

### Task 4: Typed API client (`client.ts`)

**Files:**
- Create: `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`

- [ ] **Step 1: Write the failing tests** — `frontend/src/api/client.test.ts`

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { getHome, postChat, wikiPage } from "./client";

function mockFetch(body: unknown, ok = true) {
  const fn = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("getHome GETs /api/home and returns parsed json", async () => {
    const fn = mockFetch({ ongoing: [], goals: [], metrics: [], approvals: [] });
    const home = await getHome();
    expect(fn).toHaveBeenCalledWith("/api/home", expect.objectContaining({ method: "GET" }));
    expect(home.goals).toEqual([]);
  });

  it("postChat POSTs text + context as JSON", async () => {
    const fn = mockFetch({ chat_id: "chat_1", reply: "ok", actions: [] });
    const res = await postChat("hello", { chatId: "chat_1", context: { type: "wiki_page", path: "a.md" } });
    expect(res.chat_id).toBe("chat_1");
    const [url, opts] = fn.mock.calls[0];
    expect(url).toBe("/api/chat");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({
      text: "hello", chat_id: "chat_1", context: { type: "wiki_page", path: "a.md" },
    });
  });

  it("wikiPage encodes the path query", async () => {
    const fn = mockFetch({ path: "goals/x.md", frontmatter: {}, body: "hi" });
    await wikiPage("goals/x.md");
    expect(fn.mock.calls[0][0]).toBe("/api/wiki/page?path=goals%2Fx.md");
  });

  it("throws on non-ok response", async () => {
    mockFetch({ detail: "boom" }, false);
    await expect(getHome()).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: FAIL — cannot resolve `./client`.

- [ ] **Step 3: Write `frontend/src/api/client.ts`**

```ts
export interface Tile {
  type: string;
  id?: string;
  title?: string;
  [k: string]: unknown;
}
export interface Home {
  ongoing: Tile[];
  goals: Tile[];
  metrics: Tile[];
  approvals: Tile[];
}
export interface ChatMessage {
  role: string;
  content: string;
  tool_steps: { tool: string; input: unknown }[];
}
export interface ChatResult {
  chat_id: string;
  reply: string;
  actions: { tool: string; input: unknown }[];
}
export interface WikiPage {
  path: string;
  frontmatter: Record<string, unknown>;
  body: string;
}
export type ViewContext = { type: "wiki_page"; path: string } | null;

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { method: "GET", ...init });
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return (await res.json()) as T;
}

function postJSON<T>(url: string, body: unknown): Promise<T> {
  return req<T>(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const getHome = () => req<Home>("/api/home");
export const getItems = () => req<unknown[]>("/items");
export const capture = (text: string) => postJSON<ChatResult>("/capture", { text });
export const getChats = () => req<{ id: string; title: string | null }[]>("/api/chats");
export const getChat = (id: string) =>
  req<{ id: string; messages: ChatMessage[] }>(`/api/chats/${encodeURIComponent(id)}`);
export const persistChat = (id: string) =>
  postJSON<{ chat_id: string }>(`/api/chats/${encodeURIComponent(id)}/persist`, {});
export const wikiPage = (path: string) =>
  req<WikiPage>(`/api/wiki/page?path=${encodeURIComponent(path)}`);
export const wikiIndex = () => req<{ index: string }>("/api/wiki/index");

export function postChat(
  text: string,
  opts: { chatId?: string; context?: ViewContext } = {},
): Promise<ChatResult> {
  return postJSON<ChatResult>("/api/chat", {
    text,
    chat_id: opts.chatId ?? null,
    context: opts.context ?? null,
  });
}

/** Subscribe to the server's SSE stream. Returns an unsubscribe fn. */
export function subscribeEvents(onEvent: (e: { type: string; [k: string]: unknown }) => void): () => void {
  const es = new EventSource("/api/events");
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
  return () => es.close();
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `getHome` GETs `/api/home` and parses; `postChat` POSTs `{text, chat_id, context}` JSON; `wikiPage` URL-encodes the path query; non-ok responses throw.
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat(spa): typed API client + SSE subscribe"
```

---

### Task 5: App shell + base-color picker

The shell applies the persisted theme on mount, fetches the home feed, and renders its sections (minimal markup — the real tile UI is Plan 2c). The `BaseColorPicker` changes the base hue live.

**Files:**
- Create: `frontend/src/components/BaseColorPicker.tsx`, `frontend/src/components/BaseColorPicker.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/BaseColorPicker.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BaseColorPicker } from "./BaseColorPicker";
import { deriveTheme } from "../theme/derive";
import { loadBase } from "../theme/theme";

describe("BaseColorPicker", () => {
  it("applies and persists a new base hue on change", async () => {
    localStorage.clear();
    render(<BaseColorPicker />);
    const input = screen.getByLabelText(/base color/i) as HTMLInputElement;
    await userEvent.clear(input).catch(() => {});
    // color inputs don't support clear/type; fire a change directly
    input.value = "#3a52b0";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(loadBase()).toBe("#3a52b0");
    expect(document.documentElement.style.getPropertyValue("--accent")).toBe(
      deriveTheme("#3a52b0").accent,
    );
  });
});
```

`frontend/src/App.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api/client", () => ({
  getHome: vi.fn().mockResolvedValue({
    ongoing: [{ type: "ongoing", id: "evt_1", title: "Workout" }],
    goals: [{ type: "goal", id: "item_1", title: "Squat 2x BW" }],
    metrics: [],
    approvals: [],
  }),
}));

afterEach(() => vi.clearAllMocks());

describe("App shell", () => {
  it("renders home sections from the API", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("Workout")).toBeInTheDocument());
    expect(screen.getByText("Squat 2x BW")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/components/BaseColorPicker.test.tsx src/App.test.tsx`
Expected: FAIL — cannot resolve `./BaseColorPicker`; App has no home rendering.

- [ ] **Step 3: Write `frontend/src/components/BaseColorPicker.tsx`**

```tsx
import { useState } from "react";

import { applyBase, loadBase, saveBase } from "../theme/theme";

export function BaseColorPicker() {
  const [base, setBase] = useState(loadBase);

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const hex = e.target.value;
    setBase(hex);
    saveBase(hex);
    applyBase(hex);
  }

  return (
    <label>
      Base color
      <input type="color" aria-label="Base color" value={base} onChange={onChange} />
    </label>
  );
}
```

- [ ] **Step 4: Write `frontend/src/App.tsx`**

```tsx
import { useEffect, useState } from "react";

import { getHome, Home } from "./api/client";
import { BaseColorPicker } from "./components/BaseColorPicker";

export default function App() {
  const [home, setHome] = useState<Home | null>(null);

  useEffect(() => {
    getHome().then(setHome).catch(() => setHome(null));
  }, []);

  return (
    <main style={{ background: "var(--bg)", color: "var(--text)", minHeight: "100vh" }}>
      <header style={{ display: "flex", justifyContent: "space-between", padding: 12 }}>
        <span>PKB</span>
        <BaseColorPicker />
      </header>
      {home && (
        <>
          <section aria-label="ongoing">
            {home.ongoing.map((t) => (
              <div key={t.id}>{t.title}</div>
            ))}
          </section>
          <section aria-label="goals">
            {home.goals.map((t) => (
              <div key={t.id}>{t.title}</div>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
```

- [ ] **Step 5: Update `frontend/src/main.tsx`** to apply the persisted theme before render

```tsx
import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { applyBase, loadBase } from "./theme/theme";

applyBase(loadBase());

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd frontend && npx vitest run src/components/BaseColorPicker.test.tsx src/App.test.tsx`
Expected: PASS.

- [ ] **Step 7: Merge gate, then commit**

**Unit-test plan:** `BaseColorPicker` change persists the base and applies the derived accent CSS var; `App` renders ongoing + goal titles fetched from the (mocked) API. `npm run build` still succeeds.
Gate: `cd frontend && npm test` green AND `npm run build` succeeds. Commit only if green.

```bash
git add frontend/src/components frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/main.tsx
git commit -m "feat(spa): app shell + live base-color picker"
```

---

### Task 6: Serve the built SPA from FastAPI (`PKB_SPA_DIR`)

Wire the backend so a built `frontend/dist` is actually served. Plan 2a (Task 9) added `create_app(..., spa_dir=...)` and `main.build_app` passes `settings.spa_dir`; this task makes `get_settings` populate `spa_dir` from the `PKB_SPA_DIR` env var.

**Files:**
- Modify: `pkb/config.py` (`get_settings`)
- Create: `tests/test_config_spa.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_config_spa.py`

```python
from pathlib import Path

from pkb.config import get_settings


def test_spa_dir_none_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PKB_SPA_DIR", raising=False)
    assert get_settings(tmp_path).spa_dir is None


def test_spa_dir_from_env(monkeypatch, tmp_path):
    dist = tmp_path / "frontend" / "dist"
    monkeypatch.setenv("PKB_SPA_DIR", str(dist))
    s = get_settings(tmp_path)
    assert s.spa_dir == dist.resolve()
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_config_spa.py -v`
Expected: FAIL — `spa_dir` stays `None` even with the env var set.

- [ ] **Step 3: Edit `pkb/config.py`** — make `get_settings` read `PKB_SPA_DIR`

```python
def get_settings(vault_dir: Path | None = None) -> Settings:
    if vault_dir is None:
        vault_dir = Path(os.environ.get("PKB_VAULT_DIR", "./vault"))
    spa_env = os.environ.get("PKB_SPA_DIR")
    spa_dir = Path(spa_env).resolve() if spa_env else None
    return Settings(vault_dir=Path(vault_dir).resolve(), spa_dir=spa_dir)
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_config_spa.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Final merge gate, then commit**

**Unit-test plan:** `get_settings` leaves `spa_dir` None without the env var and resolves `PKB_SPA_DIR` to an absolute path when set. The Plan 2a SPA-hosting tests already prove `create_app(spa_dir=...)` serves `index.html` + deep links.
Backend gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — whole Python suite green (prior + 2 new); 0 failed. Frontend gate: `cd frontend && npm test` green. Commit only if both green.

```bash
git add pkb/config.py tests/test_config_spa.py
git commit -m "feat(web): get_settings reads PKB_SPA_DIR to serve the built SPA"
```

- [ ] **Step 6: Manual end-to-end smoke (optional)**

```bash
cd frontend && npm run build && cd ..
PKB_VAULT_DIR=./vault PKB_SPA_DIR=./frontend/dist .venv/bin/python -m pkb.main &
curl -s localhost:8787/ | grep -o '<title>PKB</title>'
curl -s localhost:8787/api/home | python -m json.tool
```
Expected: the SPA `index.html` at `/`, and the JSON home feed at `/api/home`, from one process.

---

## Self-Review

**Spec coverage (web-app spec → this plan):**
- Vite + React + TS SPA served by FastAPI → Tasks 1, 6 (build + `PKB_SPA_DIR`; serving mechanism from Plan 2a Task 9).
- Themeable dark UI, OKLCH-derived from a base hue, forest default, settings color wheel → Tasks 2 (derive), 3 (apply + persist + default), 5 (`BaseColorPicker`).
- Typed access to the backend + SSE → Task 4 (client + `subscribeEvents`).
- App shell rendering the home feed → Task 5 (minimal; full tile UI is Plan 2c).
- Dev proxy so the SPA can hit `/api` against uvicorn in dev → Task 1 (`vite.config.ts` proxy).

Deliberately **not** here (later plans): the real tile dashboard, tile→modal logging, the ephemeral/persistent chat UI + tool-step rendering, the desktop rail/wiki-browser/context chat, approvals UI. Those are Plans 2c/2d. This plan only stands up the app + theme + data access they build on.

**Placeholder scan:** none — every step has complete code/commands. The minimal `App` markup is intentional scaffolding (Task 5 notes the real UI is 2c), not a placeholder.

**Type/signature consistency:** `ThemeTokens` keys (`bg/surface/surface2/text/muted/accent/secondary`) are identical across `derive.ts`, `theme.ts`, and the tests. `deriveTheme` / `applyTheme` / `applyBase` / `loadBase` / `saveBase` / `DEFAULT_BASE` signatures match across Tasks 2/3/5. The API client function names + the `Home`/`ChatResult`/`WikiPage`/`ViewContext` types match the Plan 2a endpoints (`/api/home`, `/api/chat`, `/api/wiki/page`, `/capture`, `/api/chats`, `/api/events`). `Settings.spa_dir` (added Plan 2a Task 9) is what Task 6 populates.

**Notes for the implementer:** Tasks 2, 3, 4 are independent frontend modules (parallelizable); Task 5 depends on 3 + 4; Task 1 must come first (scaffold); Task 6 is backend-only and independent of the frontend tasks. Frontend tests run with `npm test` from `frontend/`; the controller runs `npm`/`uv` and commits (subagents draft).
