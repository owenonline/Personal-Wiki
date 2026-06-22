import { Tile as TileData } from "../api/client";

export function Tile({
  tile,
  variant = "default",
  onClick,
}: {
  tile: TileData;
  variant?: "ongoing" | "goal" | "default";
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      data-variant={variant}
      onClick={onClick}
      style={{
        textAlign: "left",
        background: "var(--surface)",
        color: "var(--text)",
        border: "1px solid var(--surface2)",
        borderRadius: 12,
        padding: 12,
        width: "100%",
        cursor: "pointer",
      }}
    >
      <div style={{ fontWeight: 600 }}>{tile.title}</div>
    </button>
  );
}
