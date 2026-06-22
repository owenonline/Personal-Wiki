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
