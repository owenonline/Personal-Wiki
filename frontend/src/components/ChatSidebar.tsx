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
    getChats().then(setChats).catch(() => setChats([]));
  }, []);

  return (
    <aside
      aria-label="chats"
      style={{
        position: "fixed",
        top: 0,
        bottom: 0,
        left: 0,
        width: 240,
        background: "var(--surface)",
        color: "var(--text)",
        padding: 12,
      }}
    >
      <button type="button" aria-label="Close chats" onClick={onClose}>×</button>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {chats.map((c) => (
          <li key={c.id}>
            <button type="button" onClick={() => onOpen(c.id)} style={{ width: "100%", textAlign: "left" }}>
              {c.title ?? "(untitled)"}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
