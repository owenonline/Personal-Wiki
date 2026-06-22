import { deriveTheme, ThemeTokens } from "./derive";

export const DEFAULT_BASE = "#1f6f4a"; // forest
const STORAGE_KEY = "pkb.baseHex";

export function loadBase(): string {
  return localStorage.getItem(STORAGE_KEY) ?? DEFAULT_BASE;
}

export function saveBase(hex: string): void {
  localStorage.setItem(STORAGE_KEY, hex);
}

export function applyTheme(tokens: ThemeTokens, root: HTMLElement = document.documentElement): void {
  for (const [name, value] of Object.entries(tokens)) {
    root.style.setProperty(`--${name}`, value);
  }
}

export function applyBase(hex: string, root: HTMLElement = document.documentElement): void {
  applyTheme(deriveTheme(hex), root);
}
