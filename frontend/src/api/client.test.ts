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
