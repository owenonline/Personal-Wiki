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
  const status = typeof tile.status === "string" ? tile.status : undefined;
  const meta = variant === "ongoing" ? "in progress" : status;
  const cls =
    "tile" +
    (variant === "ongoing" ? " tile--ongoing" : "") +
    (status === "done" ? " tile--done" : "");

  return (
    <button type="button" className={cls} onClick={onClick}>
      <span className="tile__title">{tile.title}</span>
      {meta && <span className="tile__meta">{meta}</span>}
      {variant === "ongoing" && (
        <>
          <span className="spacer" />
          <span className="live-dot" />
        </>
      )}
    </button>
  );
}
