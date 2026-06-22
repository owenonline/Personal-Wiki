import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TileModal } from "./TileModal";

const tile = { type: "goal", id: "item_1", title: "Guitar" };

describe("TileModal", () => {
  it("submits typed text and closes", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(<TileModal tile={tile} onSubmit={onSubmit} onClose={onClose} />);
    expect(screen.getByText("Guitar")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox"), "did 25 min");
    await userEvent.click(screen.getByRole("button", { name: /log/i }));
    expect(onSubmit).toHaveBeenCalledWith("did 25 min");
    expect(onClose).toHaveBeenCalled();
  });

  it("closes without submitting on cancel", async () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();
    render(<TileModal tile={tile} onSubmit={onSubmit} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
