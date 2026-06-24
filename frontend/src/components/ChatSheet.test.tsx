import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const postChat = vi.fn();
const persistChat = vi.fn();
const getChat = vi.fn();
vi.mock("../api/client", () => ({
  postChat: (...a: unknown[]) => postChat(...a),
  persistChat: (...a: unknown[]) => persistChat(...a),
  getChat: (...a: unknown[]) => getChat(...a),
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

  it("renders the assistant reply as markdown", async () => {
    postChat.mockResolvedValue({ chat_id: "c", reply: "**bold**\n\n- one\n- two", actions: [] });
    render(<ChatSheet onClose={() => {}} />);
    await userEvent.type(screen.getByRole("textbox"), "x{enter}");
    await screen.findByRole("list");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.queryByText("- one")).toBeNull(); // rendered, not raw markdown
  });

  it("keeps (persists) the chat once it has an id", async () => {
    postChat.mockResolvedValue({ chat_id: "chat_1", reply: "ok", actions: [] });
    render(<ChatSheet onClose={() => {}} />);
    await userEvent.type(screen.getByRole("textbox"), "hi{enter}");
    await screen.findByText("ok");
    await userEvent.click(screen.getByRole("button", { name: /keep/i }));
    await waitFor(() => expect(persistChat).toHaveBeenCalledWith("chat_1"));
    expect(await screen.findByText("Kept ✓")).toBeInTheDocument();
  });

  it("restores an existing chat's messages and shows it as kept", async () => {
    getChat.mockResolvedValue({
      id: "c5",
      messages: [
        { role: "user", content: "earlier question", tool_steps: [] },
        { role: "assistant", content: "earlier answer", tool_steps: [] },
      ],
    });
    render(<ChatSheet onClose={() => {}} existingChatId="c5" />);
    expect(await screen.findByText("earlier question")).toBeInTheDocument();
    expect(screen.getByText("earlier answer")).toBeInTheDocument();
    expect(screen.getByText("Kept ✓")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "chat" })).toHaveClass("sheet--full");
  });

  it("shows the sidebar hamburger only in full-screen view", async () => {
    const onOpenSidebar = vi.fn();
    // Partial (fresh) chat: no hamburger.
    const { unmount } = render(<ChatSheet onClose={() => {}} onOpenSidebar={onOpenSidebar} />);
    expect(screen.queryByRole("button", { name: /open chats/i })).toBeNull();
    unmount();

    // Full-screen (opened from sidebar): hamburger present and wired.
    getChat.mockResolvedValue({ id: "c6", messages: [] });
    render(<ChatSheet onClose={() => {}} existingChatId="c6" onOpenSidebar={onOpenSidebar} />);
    await userEvent.click(await screen.findByRole("button", { name: /open chats/i }));
    expect(onOpenSidebar).toHaveBeenCalled();
  });
});
