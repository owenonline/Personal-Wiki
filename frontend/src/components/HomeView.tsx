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
    <>
      {home.ongoing.length > 0 && (
        <>
          <div className="section-label">ongoing</div>
          <section className="tiles" aria-label="ongoing">
            {home.ongoing.map((t) => (
              <Tile key={t.id} tile={t} variant="ongoing" onClick={() => onTileClick(t)} />
            ))}
          </section>
        </>
      )}
      <div className="section-label">today</div>
      <section className="tiles" aria-label="goals">
        {home.goals.map((t) => (
          <Tile key={t.id} tile={t} variant="goal" onClick={() => onTileClick(t)} />
        ))}
      </section>
    </>
  );
}
