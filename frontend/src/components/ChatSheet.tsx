import { useState } from "react";

import { persistChat, ViewContext } from "../api/client";
import { useChat } from "../hooks/useChat";
import { ToolSteps } from "./ToolSteps";

export function ChatSheet({
  onClose,
  context = null,
}: {
  onClose: () => void;
  context?: ViewContext;
}) {
  const { chatId, messages, send } = useChat();
  const [text, setText] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setText("");
    await send(t, context);
  }

  return (
    <div
      role="dialog"
      aria-label="chat"
      style={{
        position: "fixed",
        left: 0,
        right: 0,
        bottom: 0,
        height: "66%",
        background: "var(--surface)",
        color: "var(--text)",
        borderRadius: "16px 16px 0 0",
        display: "flex",
        flexDirection: "column",
        padding: 12,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button type="button" disabled={!chatId} onClick={() => chatId && persistChat(chatId)}>
          Keep
        </button>
        <button type="button" aria-label="Close chat" onClick={onClose}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div>{m.content}</div>
            {m.role === "assistant" && <ToolSteps steps={m.tool_steps} />}
          </div>
        ))}
      </div>
      <form onSubmit={onSubmit}>
        <input
          aria-label="chat input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type anything…"
          style={{ width: "100%", padding: 8 }}
        />
      </form>
    </div>
  );
}
