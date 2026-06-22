# PKB Mobile Core (Plan 2c) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. For visual polish during execution, apply the **frontend-design** skill — this plan locks structure + behavior + tests; the look (spacing, motion, tile styling per the approved mockups) is refined in the components.

**Goal:** Build the mobile home experience from the mockups on top of Plan 2b's scaffold/theme/API client — a dynamic tile dashboard with live (SSE) updates, tap-a-tile→modal free-text logging, and the "type anything" → ephemeral chat that shows the agent's tool steps inline and can be kept (persisted) and reopened from a chat sidebar.

**Architecture:** React function components + small hooks over the Plan 2b API client. `useHome` fetches the tile feed and re-fetches on the SSE `home_changed` event (the live loop: log → backend files → SSE → tiles update). `useChat` drives a chat session against `/api/chat`, rendering assistant `tool_steps` as chips. State (which modal/sheet/sidebar is open) lives in `App`. Styling uses the theme CSS vars from Plan 2b. All logic is unit-tested with Vitest + Testing Library (jsdom); the drag-to-expand gesture is represented as an explicit control for testability (the literal drag affordance is a visual enhancement).

**Tech Stack:** React 18 + TypeScript, Vitest + @testing-library/react + user-event (all from Plan 2b). No new deps.

---

## File Structure

```
frontend/src/
  hooks/
    useHome.ts        # NEW: home feed + SSE-driven refresh
    useHome.test.ts   # NEW
    useChat.ts        # NEW: chat session (send -> postChat -> messages)
    useChat.test.ts   # NEW
  components/
    Tile.tsx              # NEW: one tile (title/subtitle/variant/onClick)
    HomeView.tsx          # NEW: ongoing + goals tiles from a Home
    HomeView.test.tsx     # NEW
    TileModal.tsx         # NEW: free-text logging modal
    TileModal.test.tsx    # NEW
    ToolSteps.tsx         # NEW: render assistant tool_steps as chips
    ChatSheet.tsx         # NEW: ephemeral chat sheet + keep/expand
    ChatSheet.test.tsx    # NEW
    ChatSidebar.tsx       # NEW: list persistent chats
    ChatSidebar.test.tsx  # NEW
  App.tsx               # MODIFY: compose dashboard + capture bar + sheet + sidebar + modal
  App.test.tsx          # MODIFY: integration
```

Each task is TDD and ends in the **merge gate** (same convention as 2b): from `frontend/`, `npm test` (Vitest) green, and `npm run build` succeeds at the end of the final task. Paste the summary line; commit only when green. The controller runs `npm` and commits; subagents draft.

Baseline: Plan 2b leaves **15 frontend tests** passing.

---

### Task 1: `useHome` — feed + live refresh

**Files:**
- Create: `frontend/src/hooks/useHome.ts`, `frontend/src/hooks/useHome.test.ts`

- [ ] **Step 1: Write the failing test** — `frontend/src/hooks/useHome.test.ts`

```ts
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const home1 = { ongoing: [], goals: [{ type: "goal", id: "g1", title: "A" }], metrics: [], approvals: [] };
const home2 = { ongoing: [], goals: [{ type: "goal", id: "g1", title: "A (updated)" }], metrics: [], approvals: [] };

const getHome = vi.fn();
let sseHandler: (e: { type: string }) => void = () => {};
const subscribeEvents = vi.fn((cb: (e: { type: string }) => void) => {
  sseHandler = cb;
  return () => {};
});

vi.mock("../api/client", () => ({ getHome: (...a: unknown[]) => getHome(...a), subscribeEvents: (cb: never) => subscribeEvents(cb) }));

import { useHome } from "./useHome";

afterEach(() => vi.clearAllMocks());

describe("useHome", () => {
  it("loads the feed then refetches on a home_changed SSE event", async () => {
    getHome.mockResolvedValueOnce(home1).mockResolvedValueOnce(home2);
    const { result } = renderHook(() => useHome());
    await waitFor(() => expect(result.current.home?.goals[0].title).toBe("A"));
    sseHandler({ type: "home_changed" });
    await waitFor(() => expect(result.current.home?.goals[0].title).toBe("A (updated)"));
    expect(getHome).toHaveBeenCalledTimes(2);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/hooks/useHome.test.ts`
Expected: FAIL — cannot resolve `./useHome`.

- [ ] **Step 3: Write `frontend/src/hooks/useHome.ts`**

```ts
import { useCallback, useEffect, useState } from "react";

import { getHome, Home, subscribeEvents } from "../api/client";

export function useHome() {
  const [home, setHome] = useState<Home | null>(null);

  const refresh = useCallback(() => {
    getHome()
      .then(setHome)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const unsubscribe = subscribeEvents((e) => {
      if (e.type === "home_changed") refresh();
    });
    return unsubscribe;
  }, [refresh]);

  return { home, refresh };
}
```

(Note: `useCallback` is imported from `react`.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/useHome.test.ts`
Expected: PASS.

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `useHome` loads the feed, and a `home_changed` SSE event triggers a refetch (the live loop).
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/hooks/useHome.ts frontend/src/hooks/useHome.test.ts
git commit -m "feat(spa): useHome — feed + SSE-driven live refresh"
```

---

### Task 2: Tile + HomeView

**Files:**
- Create: `frontend/src/components/Tile.tsx`, `frontend/src/components/HomeView.tsx`, `frontend/src/components/HomeView.test.tsx`

- [ ] **Step 1: Write the failing test** — `frontend/src/components/HomeView.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HomeView } from "./HomeView";

const home = {
  ongoing: [{ type: "ongoing", id: "evt_1", title: "Workout" }],
  goals: [{ type: "goal", id: "item_1", title: "Squat 2x BW" }],
  metrics: [],
  approvals: [],
};

describe("HomeView", () => {
  it("renders ongoing and goal tiles", () => {
    render(<HomeView home={home} onTileClick={() => {}} />);
    expect(screen.getByText("Workout")).toBeInTheDocument();
    expect(screen.getByText("Squat 2x BW")).toBeInTheDocument();
  });

  it("calls onTileClick with the tile when tapped", async () => {
    const onTileClick = vi.fn();
    render(<HomeView home={home} onTileClick={onTileClick} />);
    await userEvent.click(screen.getByText("Squat 2x BW"));
    expect(onTileClick).toHaveBeenCalledWith(home.goals[0]);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/components/HomeView.test.tsx`
Expected: FAIL — cannot resolve `./HomeView`.

- [ ] **Step 3: Write `frontend/src/components/Tile.tsx`**

```tsx
import { Tile as TileData } from "../api/client";

export function Tile({
  tile,
  variant = "default",
  onClick,
}: {
  tile: TileData;
  variant?: "ongoing" | "goal" | "default";
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      data-variant={variant}
      onClick={onClick}
      style={{
        textAlign: "left",
        background: "var(--surface)",
        color: "var(--text)",
        border: "1px solid var(--surface2)",
        borderRadius: 12,
        padding: 12,
        width: "100%",
        cursor: "pointer",
      }}
    >
      <div style={{ fontWeight: 600 }}>{tile.title}</div>
    </button>
  );
}
```

- [ ] **Step 4: Write `frontend/src/components/HomeView.tsx`**

```tsx
import { Home, Tile as TileData } from "../api/client";
import { Tile } from "./Tile";

export function HomeView({
  home,
  onTileClick,
}: {
  home: Home;
  onTileClick: (tile: TileData) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12 }}>
      {home.ongoing.length > 0 && (
        <section aria-label="ongoing" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {home.ongoing.map((t) => (
            <Tile key={t.id} tile={t} variant="ongoing" onClick={() => onTileClick(t)} />
          ))}
        </section>
      )}
      <section
        aria-label="goals"
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}
      >
        {home.goals.map((t) => (
          <Tile key={t.id} tile={t} variant="goal" onClick={() => onTileClick(t)} />
        ))}
      </section>
    </div>
  );
}
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd frontend && npx vitest run src/components/HomeView.test.tsx`
Expected: PASS.

- [ ] **Step 6: Merge gate, then commit**

**Unit-test plan:** `HomeView` renders ongoing + goal tiles; tapping a tile calls `onTileClick` with that tile.
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/components/Tile.tsx frontend/src/components/HomeView.tsx frontend/src/components/HomeView.test.tsx
git commit -m "feat(spa): tile + home dashboard view"
```

---

### Task 3: TileModal — free-text logging

**Files:**
- Create: `frontend/src/components/TileModal.tsx`, `frontend/src/components/TileModal.test.tsx`

- [ ] **Step 1: Write the failing test** — `frontend/src/components/TileModal.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TileModal } from "./TileModal";

const tile = { type: "goal", id: "item_1", title: "Guitar" };

describe("TileModal", () => {
  it("submits typed text and closes", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(<TileModal tile={tile} onSubmit={onSubmit} onClose={onClose} />);
    expect(screen.getByText("Guitar")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox"), "did 25 min");
    await userEvent.click(screen.getByRole("button", { name: /log/i }));
    expect(onSubmit).toHaveBeenCalledWith("did 25 min");
    expect(onClose).toHaveBeenCalled();
  });

  it("closes without submitting on cancel", async () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();
    render(<TileModal tile={tile} onSubmit={onSubmit} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/components/TileModal.test.tsx`
Expected: FAIL — cannot resolve `./TileModal`.

- [ ] **Step 3: Write `frontend/src/components/TileModal.tsx`**

```tsx
import { useState } from "react";

import { Tile as TileData } from "../api/client";

export function TileModal({
  tile,
  onSubmit,
  onClose,
}: {
  tile: TileData;
  onSubmit: (text: string) => Promise<void> | void;
  onClose: () => void;
}) {
  const [text, setText] = useState("");

  async function log() {
    if (text.trim()) await onSubmit(text.trim());
    onClose();
  }

  return (
    <div
      role="dialog"
      aria-label={tile.title}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "flex-end",
      }}
    >
      <div style={{ background: "var(--surface)", color: "var(--text)", width: "100%", padding: 16, borderRadius: "16px 16px 0 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <strong>{tile.title}</strong>
          <button type="button" aria-label="Close" onClick={onClose}>×</button>
        </div>
        <input
          aria-label="log entry"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="log…"
          style={{ width: "100%", marginTop: 8, padding: 8 }}
        />
        <button type="button" onClick={log} style={{ marginTop: 8 }}>Log</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/components/TileModal.test.tsx`
Expected: PASS.

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** the modal shows the tile title; typing + Log calls `onSubmit(text)` then `onClose`; Close calls `onClose` without submitting.
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/components/TileModal.tsx frontend/src/components/TileModal.test.tsx
git commit -m "feat(spa): tile logging modal"
```

---

### Task 4: useChat + ToolSteps + ChatSheet (ephemeral)

**Files:**
- Create: `frontend/src/hooks/useChat.ts`, `frontend/src/hooks/useChat.test.ts`
- Create: `frontend/src/components/ToolSteps.tsx`
- Create: `frontend/src/components/ChatSheet.tsx`, `frontend/src/components/ChatSheet.test.tsx`

- [ ] **Step 1: Write the failing tests**

`frontend/src/hooks/useChat.test.ts`:

```ts
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const postChat = vi.fn();
vi.mock("../api/client", () => ({ postChat: (...a: unknown[]) => postChat(...a) }));

import { useChat } from "./useChat";

afterEach(() => vi.clearAllMocks());

describe("useChat", () => {
  it("appends user + assistant messages and tracks chat id", async () => {
    postChat.mockResolvedValue({ chat_id: "chat_1", reply: "Logged.", actions: [{ tool: "record_event", input: {} }] });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send("bench 135x5");
    });
    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages[0]).toMatchObject({ role: "user", content: "bench 135x5" });
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", content: "Logged." });
    expect(result.current.messages[1].tool_steps[0].tool).toBe("record_event");
    expect(result.current.chatId).toBe("chat_1");
  });
});
```

`frontend/src/components/ChatSheet.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const postChat = vi.fn();
vi.mock("../api/client", () => ({
  postChat: (...a: unknown[]) => postChat(...a),
  persistChat: vi.fn(),
}));

import { ChatSheet } from "./ChatSheet";

afterEach(() => vi.clearAllMocks());

describe("ChatSheet", () => {
  it("sends a message and shows the reply with a tool-step chip", async () => {
    postChat.mockResolvedValue({
      chat_id: "chat_1",
      reply: "Done.",
      actions: [{ tool: "update_event", input: {} }],
    });
    render(<ChatSheet onClose={() => {}} />);
    await userEvent.type(screen.getByRole("textbox"), "guitar 30/day{enter}");
    expect(await screen.findByText("Done.")).toBeInTheDocument();
    expect(screen.getByText(/update_event/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd frontend && npx vitest run src/hooks/useChat.test.ts src/components/ChatSheet.test.tsx`
Expected: FAIL — cannot resolve `./useChat` / `./ChatSheet`.

- [ ] **Step 3: Write `frontend/src/hooks/useChat.ts`**

```ts
import { useState } from "react";

import { ChatMessage, postChat, ViewContext } from "../api/client";

export function useChat(initialChatId: string | null = null) {
  const [chatId, setChatId] = useState<string | null>(initialChatId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  async function send(text: string, context: ViewContext = null) {
    setMessages((m) => [...m, { role: "user", content: text, tool_steps: [] }]);
    const res = await postChat(text, { chatId: chatId ?? undefined, context });
    setChatId(res.chat_id);
    setMessages((m) => [...m, { role: "assistant", content: res.reply, tool_steps: res.actions }]);
    return res;
  }

  return { chatId, messages, send };
}
```

- [ ] **Step 4: Write `frontend/src/components/ToolSteps.tsx`**

```tsx
import { ChatMessage } from "../api/client";

export function ToolSteps({ steps }: { steps: ChatMessage["tool_steps"] }) {
  if (!steps.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
      {steps.map((s, i) => (
        <span
          key={i}
          style={{
            fontSize: 11,
            color: "var(--muted)",
            border: "1px dashed var(--surface2)",
            borderRadius: 6,
            padding: "1px 6px",
          }}
        >
          🔧 {s.tool}
        </span>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Write `frontend/src/components/ChatSheet.tsx`**

```tsx
import { useState } from "react";

import { persistChat, ViewContext } from "../api/client";
import { useChat } from "../hooks/useChat";
import { ToolSteps } from "./ToolSteps";

export function ChatSheet({
  onClose,
  context = null,
}: {
  onClose: () => void;
  context?: ViewContext;
}) {
  const { chatId, messages, send } = useChat();
  const [text, setText] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setText("");
    await send(t, context);
  }

  return (
    <div
      role="dialog"
      aria-label="chat"
      style={{
        position: "fixed",
        left: 0,
        right: 0,
        bottom: 0,
        height: "66%",
        background: "var(--surface)",
        color: "var(--text)",
        borderRadius: "16px 16px 0 0",
        display: "flex",
        flexDirection: "column",
        padding: 12,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button type="button" disabled={!chatId} onClick={() => chatId && persistChat(chatId)}>
          Keep
        </button>
        <button type="button" aria-label="Close chat" onClick={onClose}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div>{m.content}</div>
            {m.role === "assistant" && <ToolSteps steps={m.tool_steps} />}
          </div>
        ))}
      </div>
      <form onSubmit={onSubmit}>
        <input
          aria-label="chat input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type anything…"
          style={{ width: "100%", padding: 8 }}
        />
      </form>
    </div>
  );
}
```

- [ ] **Step 6: Run to verify they pass**

Run: `cd frontend && npx vitest run src/hooks/useChat.test.ts src/components/ChatSheet.test.tsx`
Expected: PASS.

- [ ] **Step 7: Merge gate, then commit**

**Unit-test plan:** `useChat.send` appends user + assistant messages and tracks `chat_id`; `ChatSheet` sends a message and renders the reply + a tool-step chip (`🔧 update_event`).
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/hooks/useChat.ts frontend/src/hooks/useChat.test.ts frontend/src/components/ToolSteps.tsx frontend/src/components/ChatSheet.tsx frontend/src/components/ChatSheet.test.tsx
git commit -m "feat(spa): ephemeral chat sheet with inline tool steps"
```

---

### Task 5: Chat sidebar (persistent chats)

**Files:**
- Create: `frontend/src/components/ChatSidebar.tsx`, `frontend/src/components/ChatSidebar.test.tsx`

- [ ] **Step 1: Write the failing test** — `frontend/src/components/ChatSidebar.test.tsx`

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const getChats = vi.fn();
vi.mock("../api/client", () => ({ getChats: (...a: unknown[]) => getChats(...a) }));

import { ChatSidebar } from "./ChatSidebar";

afterEach(() => vi.clearAllMocks());

describe("ChatSidebar", () => {
  it("lists persistent chats and opens one", async () => {
    getChats.mockResolvedValue([{ id: "chat_1", title: "Workout review" }]);
    const onOpen = vi.fn();
    render(<ChatSidebar onOpen={onOpen} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("Workout review")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Workout review"));
    expect(onOpen).toHaveBeenCalledWith("chat_1");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/components/ChatSidebar.test.tsx`
Expected: FAIL — cannot resolve `./ChatSidebar`.

- [ ] **Step 3: Write `frontend/src/components/ChatSidebar.tsx`**

```tsx
import { useEffect, useState } from "react";

import { getChats } from "../api/client";

export function ChatSidebar({
  onOpen,
  onClose,
}: {
  onOpen: (chatId: string) => void;
  onClose: () => void;
}) {
  const [chats, setChats] = useState<{ id: string; title: string | null }[]>([]);

  useEffect(() => {
    getChats().then(setChats).catch(() => setChats([]));
  }, []);

  return (
    <aside
      aria-label="chats"
      style={{
        position: "fixed",
        top: 0,
        bottom: 0,
        left: 0,
        width: 240,
        background: "var(--surface)",
        color: "var(--text)",
        padding: 12,
      }}
    >
      <button type="button" aria-label="Close chats" onClick={onClose}>×</button>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {chats.map((c) => (
          <li key={c.id}>
            <button type="button" onClick={() => onOpen(c.id)} style={{ width: "100%", textAlign: "left" }}>
              {c.title ?? "(untitled)"}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/components/ChatSidebar.test.tsx`
Expected: PASS.

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `ChatSidebar` lists persistent chats from `getChats` and calls `onOpen(chatId)` when one is tapped.
Gate: `cd frontend && npm test` green. Commit only if green.

```bash
git add frontend/src/components/ChatSidebar.tsx frontend/src/components/ChatSidebar.test.tsx
git commit -m "feat(spa): persistent chat sidebar"
```

---

### Task 6: Compose the mobile app (`App.tsx`)

Wire it together: `☰` opens the sidebar, the dashboard renders tiles (tap → `TileModal` whose submit `capture()`s the text — the SSE loop updates the tile), and the bottom "Type anything…" bar opens the `ChatSheet`.

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing tests** — replace `frontend/src/App.test.tsx`

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const getHome = vi.fn().mockResolvedValue({
  ongoing: [{ type: "ongoing", id: "evt_1", title: "Workout" }],
  goals: [{ type: "goal", id: "item_1", title: "Squat 2x BW" }],
  metrics: [],
  approvals: [],
});
const capture = vi.fn().mockResolvedValue({ chat_id: "c", reply: "ok", actions: [] });

vi.mock("./api/client", () => ({
  getHome: (...a: unknown[]) => getHome(...a),
  capture: (...a: unknown[]) => capture(...a),
  subscribeEvents: () => () => {},
  postChat: vi.fn(),
  persistChat: vi.fn(),
  getChats: vi.fn().mockResolvedValue([]),
}));

import App from "./App";

afterEach(() => vi.clearAllMocks());

describe("mobile App", () => {
  it("renders tiles from the home feed", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("Workout")).toBeInTheDocument());
    expect(screen.getByText("Squat 2x BW")).toBeInTheDocument();
  });

  it("opens the chat sheet from the capture bar", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /type anything/i }));
    expect(screen.getByRole("dialog", { name: "chat" })).toBeInTheDocument();
  });

  it("tapping a tile opens its logging modal and captures on submit", async () => {
    render(<App />);
    await waitFor(() => screen.getByText("Squat 2x BW"));
    await userEvent.click(screen.getByText("Squat 2x BW"));
    await userEvent.type(screen.getByLabelText("log entry"), "did a heavy single");
    await userEvent.click(screen.getByRole("button", { name: /log/i }));
    expect(capture).toHaveBeenCalledWith("did a heavy single");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: FAIL — the old `App` has no capture bar / tiles wiring.

- [ ] **Step 3: Write `frontend/src/App.tsx`**

```tsx
import { useState } from "react";

import { capture, Tile as TileData } from "./api/client";
import { BaseColorPicker } from "./components/BaseColorPicker";
import { ChatSheet } from "./components/ChatSheet";
import { ChatSidebar } from "./components/ChatSidebar";
import { HomeView } from "./components/HomeView";
import { TileModal } from "./components/TileModal";
import { useHome } from "./hooks/useHome";

export default function App() {
  const { home, refresh } = useHome();
  const [chatOpen, setChatOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modalTile, setModalTile] = useState<TileData | null>(null);

  return (
    <main style={{ background: "var(--bg)", color: "var(--text)", minHeight: "100vh", paddingBottom: 64 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12 }}>
        <button type="button" aria-label="Open chats" onClick={() => setSidebarOpen(true)}>☰</button>
        <span>PKB</span>
        <BaseColorPicker />
      </header>

      {home && <HomeView home={home} onTileClick={setModalTile} />}

      <div style={{ position: "fixed", left: 0, right: 0, bottom: 0, padding: 8, background: "var(--bg)" }}>
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          style={{
            width: "100%",
            textAlign: "left",
            padding: 12,
            borderRadius: 20,
            background: "var(--surface)",
            color: "var(--muted)",
            border: "1px solid var(--surface2)",
          }}
        >
          Type anything…
        </button>
      </div>

      {modalTile && (
        <TileModal
          tile={modalTile}
          onSubmit={async (text) => {
            await capture(text);
            refresh();
          }}
          onClose={() => setModalTile(null)}
        />
      )}
      {chatOpen && <ChatSheet onClose={() => setChatOpen(false)} />}
      {sidebarOpen && (
        <ChatSidebar onOpen={() => setSidebarOpen(false)} onClose={() => setSidebarOpen(false)} />
      )}
    </main>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Final merge gate, then commit**

**Unit-test plan:** App renders tiles from the feed; the capture bar opens the chat sheet (a `dialog` named "chat"); tapping a tile opens its modal and submitting `capture()`s the text (then refreshes). Whole frontend suite + build green end to end.
Final gate: `cd frontend && npm test` green AND `npm run build` succeeds. Commit only if green.

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(spa): compose mobile app (tiles + modal logging + chat + sidebar)"
```

---

## Self-Review

**Spec coverage (web-app spec → this plan):**
- Dynamic tile dashboard, ongoing on top, goal/metric/approval tiles → Tasks 2, 6 (metrics/approvals arrive empty from the backend feed; their tile rendering is trivial to add when those add-ons land, and the `HomeView` already iterates the feed).
- Tap a tile → modal free-text logging, tile reacts live → Tasks 3 (modal) + 6 (capture + `useHome` SSE refresh = the live loop).
- "Type anything" → ephemeral chat with inline tool/source use → Task 4 (`ChatSheet` + `ToolSteps`).
- Keep (persist) a chat; reach saved chats via `☰` sidebar → Tasks 4 (`Keep`) + 5 (`ChatSidebar`) + 6 (`☰`).
- Live updates via SSE → Task 1 (`useHome`).

**Deliberately deferred (later plans), consistent with the spec's seams:** the literal drag-to-expand-to-fullscreen gesture (represented here as the `Keep` control — the gesture is a visual enhancement for execution); approval-tile review UI (Plan 2d, with the Tier-3 backend); metric tiles (need Apple Health); the desktop rail/wiki-browser/context-chat (Plan 2d). Visual fidelity to the mockups (motion, exact tile styling) is applied during execution via the frontend-design skill — this plan fixes structure + behavior + tests.

**Placeholder scan:** none — every step has complete code/commands. Minimal inline styling is intentional (theme-var-driven), to be polished in execution.

**Type/signature consistency:** components consume the Plan 2b client types (`Home`, `Tile`, `ChatMessage`, `ViewContext`) and functions (`getHome`, `subscribeEvents`, `postChat`, `persistChat`, `getChats`, `capture`) unchanged. `onTileClick(tile)`, `TileModal({tile,onSubmit,onClose})`, `ChatSheet({onClose,context})`, `ChatSidebar({onOpen,onClose})`, `useChat().send(text,context)`, and `useHome().{home,refresh}` signatures match between their defining task and `App` (Task 6).

**Notes for the implementer:** Tasks 1–5 are independent components/hooks (parallelizable); Task 6 composes them and must come last. `npm test` runs the whole frontend suite each gate. The controller runs `npm` and commits; subagents draft.
