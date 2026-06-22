import { Home, Tile as TileData } from "../api/client";
import { Tile } from "./Tile";

export function HomeView({
  home,
  onTileClick,
}: {
  home: Home;
  onTileClick: (tile: TileData) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12 }}>
      {home.ongoing.length > 0 && (
        <section aria-label="ongoing" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {home.ongoing.map((t) => (
            <Tile key={t.id} tile={t} variant="ongoing" onClick={() => onTileClick(t)} />
          ))}
        </section>
      )}
      <section
        aria-label="goals"
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}
      >
        {home.goals.map((t) => (
          <Tile key={t.id} tile={t} variant="goal" onClick={() => onTileClick(t)} />
        ))}
      </section>
    </div>
  );
}
