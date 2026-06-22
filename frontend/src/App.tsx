import { useState } from "react";

import { capture, Tile as TileData } from "./api/client";
import { BaseColorPicker } from "./components/BaseColorPicker";
import { ChatSheet } from "./components/ChatSheet";
import { ChatSidebar } from "./components/ChatSidebar";
import { HomeView } from "./components/HomeView";
import { TileModal } from "./components/TileModal";
import { useHome } from "./hooks/useHome";

export default function App() {
  const { home, refresh } = useHome();
  const [chatOpen, setChatOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modalTile, setModalTile] = useState<TileData | null>(null);

  return (
    <main style={{ background: "var(--bg)", color: "var(--text)", minHeight: "100vh", paddingBottom: 64 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12 }}>
        <button type="button" aria-label="Open chats" onClick={() => setSidebarOpen(true)}>☰</button>
        <span>PKB</span>
        <BaseColorPicker />
      </header>

      {home && <HomeView home={home} onTileClick={setModalTile} />}

      <div style={{ position: "fixed", left: 0, right: 0, bottom: 0, padding: 8, background: "var(--bg)" }}>
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          style={{
            width: "100%",
            textAlign: "left",
            padding: 12,
            borderRadius: 20,
            background: "var(--surface)",
            color: "var(--muted)",
            border: "1px solid var(--surface2)",
          }}
        >
          Type anything…
        </button>
      </div>

      {modalTile && (
        <TileModal
          tile={modalTile}
          onSubmit={async (text) => {
            await capture(text);
            refresh();
          }}
          onClose={() => setModalTile(null)}
        />
      )}
      {chatOpen && <ChatSheet onClose={() => setChatOpen(false)} />}
      {sidebarOpen && (
        <ChatSidebar onOpen={() => setSidebarOpen(false)} onClose={() => setSidebarOpen(false)} />
      )}
    </main>
  );
}
