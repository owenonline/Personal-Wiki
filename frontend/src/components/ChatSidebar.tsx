import { useEffect, useState } from "react";

import { getChats } from "../api/client";

export function ChatSidebar({
  onOpen,
  onClose,
}: {
  onOpen: (chatId: string) => void;
  onClose: () => void;
}) {
  const [chats, setChats] = useState<{ id: string; title: string | null }[]>([]);

  useEffect(() => {
    getChats()
      .then(setChats)
      .catch(() => setChats([]));
  }, []);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" aria-label="chats">
        <div className="drawer__top">
          <span className="drawer__title">Chats</span>
          <button className="icon-btn" type="button" aria-label="Close chats" onClick={onClose}>
            ×
          </button>
        </div>
        {chats.length === 0 && <div className="drawer__empty">No saved chats yet.</div>}
        {chats.map((c) => (
          <button key={c.id} className="chat-row" type="button" onClick={() => onOpen(c.id)}>
            {c.title ?? "(untitled)"}
          </button>
        ))}
      </aside>
    </>
  );
}
