import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const postChat = vi.fn();
const persistChat = vi.fn();
vi.mock("../api/client", () => ({
  postChat: (...a: unknown[]) => postChat(...a),
  persistChat: (...a: unknown[]) => persistChat(...a),
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

  it("keeps (persists) the chat once it has an id", async () => {
    postChat.mockResolvedValue({ chat_id: "chat_1", reply: "ok", actions: [] });
    render(<ChatSheet onClose={() => {}} />);
    await userEvent.type(screen.getByRole("textbox"), "hi{enter}");
    await screen.findByText("ok");
    await userEvent.click(screen.getByRole("button", { name: /keep/i }));
    await waitFor(() => expect(persistChat).toHaveBeenCalledWith("chat_1"));
    expect(await screen.findByText("Kept ✓")).toBeInTheDocument();
  });
});
