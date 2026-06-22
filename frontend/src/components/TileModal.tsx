import { useState } from "react";

import { Tile as TileData } from "../api/client";

export function TileModal({
  tile,
  onSubmit,
  onClose,
}: {
  tile: TileData;
  onSubmit: (text: string) => Promise<void> | void;
  onClose: () => void;
}) {
  const [text, setText] = useState("");

  async function log() {
    if (text.trim()) await onSubmit(text.trim());
    onClose();
  }

  return (
    <div
      role="dialog"
      aria-label={tile.title}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "flex-end",
      }}
    >
      <div style={{ background: "var(--surface)", color: "var(--text)", width: "100%", padding: 16, borderRadius: "16px 16px 0 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <strong>{tile.title}</strong>
          <button type="button" aria-label="Close" onClick={onClose}>×</button>
        </div>
        <input
          aria-label="log entry"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="log…"
          style={{ width: "100%", marginTop: 8, padding: 8 }}
        />
        <button type="button" onClick={log} style={{ marginTop: 8 }}>Log</button>
      </div>
    </div>
  );
}
