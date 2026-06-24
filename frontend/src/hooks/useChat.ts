import { useEffect, useState } from "react";

import { ChatMessage, getChat, postChat, ViewContext } from "../api/client";

export function useChat(initialChatId: string | null = null) {
  const [chatId, setChatId] = useState<string | null>(initialChatId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // When opened against an existing chat (e.g. from the sidebar), load its
  // history so the conversation is restored rather than starting blank.
  useEffect(() => {
    if (!initialChatId) return;
    let live = true;
    getChat(initialChatId)
      .then((c) => {
        if (live) setMessages(c.messages);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [initialChatId]);

  async function send(text: string, context: ViewContext = null) {
    setMessages((m) => [...m, { role: "user", content: text, tool_steps: [] }]);
    const res = await postChat(text, { chatId: chatId ?? undefined, context });
    setChatId(res.chat_id);
    setMessages((m) => [...m, { role: "assistant", content: res.reply, tool_steps: res.actions }]);
    return res;
  }

  return { chatId, messages, send };
}
