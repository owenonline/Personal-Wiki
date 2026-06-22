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
