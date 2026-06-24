import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const postChat = vi.fn();
const getChat = vi.fn();
vi.mock("../api/client", () => ({
  postChat: (...a: unknown[]) => postChat(...a),
  getChat: (...a: unknown[]) => getChat(...a),
}));

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
    expect(getChat).not.toHaveBeenCalled();
  });

  it("restores an existing chat's messages when given an id", async () => {
    getChat.mockResolvedValue({
      id: "chat_9",
      messages: [
        { role: "user", content: "hey", tool_steps: [] },
        { role: "assistant", content: "hi there", tool_steps: [] },
      ],
    });
    const { result } = renderHook(() => useChat("chat_9"));
    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(getChat).toHaveBeenCalledWith("chat_9");
    expect(result.current.chatId).toBe("chat_9");
    expect(result.current.messages[1].content).toBe("hi there");
  });
});
