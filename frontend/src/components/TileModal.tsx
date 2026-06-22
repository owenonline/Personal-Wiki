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
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label={tile.title}>
        <div className="sheet__handle" />
        <div className="modal__head">
          <span className="modal__title">{tile.title}</span>
          <button className="icon-btn" type="button" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal__hint">Log into this tile — type anything.</div>
        <input
          className="field"
          aria-label="log entry"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") log();
          }}
          placeholder="e.g. did 25 min, felt great"
        />
        <div className="modal__actions">
          <button className="btn-primary" type="button" onClick={log}>
            Log
          </button>
        </div>
      </div>
    </>
  );
}
