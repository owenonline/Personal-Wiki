import { beforeEach, describe, expect, it } from "vitest";

import { applyBase, applyTheme, DEFAULT_BASE, loadBase, saveBase } from "./theme";
import { deriveTheme } from "./derive";

describe("theme persistence", () => {
  beforeEach(() => localStorage.clear());

  it("defaults to the forest base", () => {
    expect(loadBase()).toBe(DEFAULT_BASE);
  });

  it("round-trips a saved base", () => {
    saveBase("#3a52b0");
    expect(loadBase()).toBe("#3a52b0");
  });
});

describe("applyTheme", () => {
  it("sets a CSS custom property per token", () => {
    const root = document.documentElement;
    applyTheme(deriveTheme("#1f6f4a"), root);
    expect(root.style.getPropertyValue("--bg")).toMatch(/^#[0-9a-f]{6}$/i);
    expect(root.style.getPropertyValue("--accent")).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("applyBase derives then applies", () => {
    const root = document.documentElement;
    root.style.removeProperty("--accent");
    applyBase("#3a52b0", root);
    expect(root.style.getPropertyValue("--accent")).toBe(deriveTheme("#3a52b0").accent);
  });
});
