import { useEffect, useRef, useState } from "react";

import { persistChat, ViewContext } from "../api/client";
import { useChat } from "../hooks/useChat";
import { Markdown } from "./Markdown";
import { ToolSteps } from "./ToolSteps";

export function ChatSheet({
  onClose,
  context = null,
  existingChatId,
}: {
  onClose: () => void;
  context?: ViewContext;
  existingChatId?: string;
}) {
  const { chatId, messages, send } = useChat(existingChatId ?? null);
  const [text, setText] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [wantKeep, setWantKeep] = useState(false);
  // A chat opened from the sidebar is already persistent.
  const [kept, setKept] = useState(Boolean(existingChatId));
  const dragStartY = useRef<number | null>(null);

  // Persist as soon as a chat id exists and the user has asked to keep it
  // (via swipe-up or the Keep button) — even if they asked before sending.
  useEffect(() => {
    if (wantKeep && chatId && !kept) {
      Promise.resolve(persistChat(chatId))
        .then(() => setKept(true))
        .catch(() => {});
    }
  }, [wantKeep, chatId, kept]);

  function keep() {
    setWantKeep(true);
  }
  function expand() {
    setExpanded(true);
    setWantKeep(true); // expanding = keeping
  }

  function onGrabDown(e: React.PointerEvent) {
    dragStartY.current = e.clientY;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function onGrabUp(e: React.PointerEvent) {
    if (dragStartY.current == null) return;
    const dy = dragStartY.current - e.clientY; // upward swipe = positive
    dragStartY.current = null;
    if (dy > 48) expand();
    else if (dy < -48) (expanded ? setExpanded(false) : onClose());
  }

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
      <div className={"sheet" + (expanded ? " sheet--full" : "")} role="dialog" aria-label="chat">
        <div className="sheet__grab" onPointerDown={onGrabDown} onPointerUp={onGrabUp}>
          <div className="sheet__handle" />
        </div>
        <div className="chat">
          <div className="chat__head">
            <button className="btn-ghost" type="button" disabled={kept} onClick={keep}>
              {kept ? "Kept ✓" : "Keep"}
            </button>
            <span className="chat__ephemeral">{kept ? "kept" : "ephemeral · swipe up to keep"}</span>
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
                <div key={i} className="msg-ai">
                  <Markdown>{m.content}</Markdown>
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
