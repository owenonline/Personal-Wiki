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
