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
  const [openChatId, setOpenChatId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modalTile, setModalTile] = useState<TileData | null>(null);

  function openChat(id: string | null) {
    setOpenChatId(id);
    setChatOpen(true);
  }
  function closeChat() {
    setChatOpen(false);
    setOpenChatId(null);
  }

  return (
    <main className="app">
      <header className="app-header">
        <button
          className="icon-btn"
          type="button"
          aria-label="Open chats"
          onClick={() => setSidebarOpen(true)}
        >
          ☰
        </button>
        <span className="wordmark">PKB</span>
        <BaseColorPicker />
      </header>

      {home && <HomeView home={home} onTileClick={setModalTile} />}

      <div className="capture-bar">
        <div className="capture-bar__inner">
          <button className="capture-btn" type="button" onClick={() => openChat(null)}>
            Type anything…<span className="caret">⌁</span>
          </button>
        </div>
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
      {chatOpen && (
        <ChatSheet
          key={openChatId ?? "new"}
          existingChatId={openChatId ?? undefined}
          onClose={closeChat}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
      )}
      {sidebarOpen && (
        <ChatSidebar
          onOpen={(id) => {
            setSidebarOpen(false);
            openChat(id);
          }}
          onClose={() => setSidebarOpen(false)}
        />
      )}
    </main>
  );
}
