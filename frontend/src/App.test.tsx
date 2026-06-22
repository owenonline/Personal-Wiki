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
