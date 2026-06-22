import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HomeView } from "./HomeView";

const home = {
  ongoing: [{ type: "ongoing", id: "evt_1", title: "Workout" }],
  goals: [{ type: "goal", id: "item_1", title: "Squat 2x BW" }],
  metrics: [],
  approvals: [],
};

describe("HomeView", () => {
  it("renders ongoing and goal tiles", () => {
    render(<HomeView home={home} onTileClick={() => {}} />);
    expect(screen.getByText("Workout")).toBeInTheDocument();
    expect(screen.getByText("Squat 2x BW")).toBeInTheDocument();
  });

  it("calls onTileClick with the tile when tapped", async () => {
    const onTileClick = vi.fn();
    render(<HomeView home={home} onTileClick={onTileClick} />);
    await userEvent.click(screen.getByText("Squat 2x BW"));
    expect(onTileClick).toHaveBeenCalledWith(home.goals[0]);
  });
});
