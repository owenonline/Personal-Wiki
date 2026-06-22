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
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label="chat">
        <div className="sheet__handle" />
        <div className="chat">
          <div className="chat__head">
            <button
              className="btn-ghost"
              type="button"
              disabled={!chatId}
              onClick={() => chatId && persistChat(chatId)}
            >
              Keep
            </button>
            <span className="chat__ephemeral">ephemeral</span>
            <button className="icon-btn" type="button" aria-label="Close chat" onClick={onClose}>
              ×
            </button>
          </div>
          <div className="chat__msgs">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="bubble bubble--me">
                  {m.content}
                </div>
              ) : (
                <div key={i} className="row-ai">
                  <div className="bubble bubble--ai">{m.content}</div>
                  <ToolSteps steps={m.tool_steps} />
                </div>
              ),
            )}
          </div>
          <form className="chat__form" onSubmit={onSubmit}>
            <input
              className="field"
              aria-label="chat input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type anything…"
            />
          </form>
        </div>
      </div>
    </>
  );
}
