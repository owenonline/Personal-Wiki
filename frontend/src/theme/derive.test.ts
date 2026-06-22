import { describe, expect, it } from "vitest";

import { deriveTheme, ThemeTokens } from "./derive";

const HEX = /^#[0-9a-f]{6}$/i;

describe("deriveTheme", () => {
  it("returns all tokens as hex strings", () => {
    const t = deriveTheme("#1f6f4a");
    const keys: (keyof ThemeTokens)[] = [
      "bg", "surface", "surface2", "text", "muted", "accent", "secondary",
    ];
    for (const k of keys) expect(t[k]).toMatch(HEX);
  });

  it("is deterministic", () => {
    expect(deriveTheme("#1f6f4a")).toEqual(deriveTheme("#1f6f4a"));
  });

  it("derives different accents for different base hues", () => {
    expect(deriveTheme("#1f6f4a").accent).not.toBe(deriveTheme("#3a52b0").accent);
  });

  it("keeps background dark and text light", () => {
    const lum = (hex: string) =>
      parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16) + parseInt(hex.slice(5, 7), 16);
    const t = deriveTheme("#1f6f4a");
    expect(lum(t.bg)).toBeLessThan(lum(t.text));
    expect(lum(t.bg)).toBeLessThan(200);
  });
});
