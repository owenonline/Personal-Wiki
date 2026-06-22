import { converter, formatHex } from "culori";

export interface ThemeTokens {
  bg: string;
  surface: string;
  surface2: string;
  text: string;
  muted: string;
  accent: string;
  secondary: string;
}

const toOklch = converter("oklch");

function hex(l: number, c: number, h: number): string {
  return formatHex({ mode: "oklch", l, c, h })!;
}

/** Derive a coherent dark palette from one base hex via OKLCH. */
export function deriveTheme(baseHex: string): ThemeTokens {
  const base = toOklch(baseHex) ?? { mode: "oklch", l: 0.5, c: 0.1, h: 150 };
  const h = base.h ?? 0;
  const baseC = base.c ?? 0.1;
  return {
    bg: hex(0.16, Math.min(baseC, 0.03), h),
    surface: hex(0.22, Math.min(baseC, 0.04), h),
    surface2: hex(0.27, Math.min(baseC, 0.05), h),
    text: hex(0.94, 0.02, h),
    muted: hex(0.68, 0.03, h),
    accent: hex(0.72, 0.15, (h + 180) % 360),
    secondary: hex(0.8, 0.1, (h + 40) % 360),
  };
}
