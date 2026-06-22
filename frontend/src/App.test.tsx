import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api/client", () => ({
  getHome: vi.fn().mockResolvedValue({
    ongoing: [{ type: "ongoing", id: "evt_1", title: "Workout" }],
    goals: [{ type: "goal", id: "item_1", title: "Squat 2x BW" }],
    metrics: [],
    approvals: [],
  }),
}));

afterEach(() => vi.clearAllMocks());

describe("App shell", () => {
  it("renders home sections from the API", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("Workout")).toBeInTheDocument());
    expect(screen.getByText("Squat 2x BW")).toBeInTheDocument();
  });
});
