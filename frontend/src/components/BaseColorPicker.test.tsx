import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BaseColorPicker } from "./BaseColorPicker";
import { deriveTheme } from "../theme/derive";
import { loadBase } from "../theme/theme";

describe("BaseColorPicker", () => {
  it("applies and persists a new base hue on change", () => {
    localStorage.clear();
    render(<BaseColorPicker />);
    const input = screen.getByLabelText(/base color/i) as HTMLInputElement;
    // fireEvent.change drives React's controlled-input value tracker so onChange fires
    fireEvent.change(input, { target: { value: "#3a52b0" } });
    expect(loadBase()).toBe("#3a52b0");
    expect(document.documentElement.style.getPropertyValue("--accent")).toBe(
      deriveTheme("#3a52b0").accent,
    );
  });
});
