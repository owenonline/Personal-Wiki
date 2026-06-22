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
