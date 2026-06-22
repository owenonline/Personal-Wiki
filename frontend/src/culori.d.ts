// Minimal ambient types for the `culori` functions we use (the package ships
// no declarations tsc resolves under "bundler" moduleResolution).
declare module "culori" {
  export interface Oklch {
    mode: string;
    l: number;
    c?: number;
    h?: number;
  }
  export function converter(
    mode: "oklch",
  ): (color: string) => Oklch | undefined;
  export function formatHex(color: {
    mode: string;
    l: number;
    c: number;
    h: number;
  }): string | undefined;
}
