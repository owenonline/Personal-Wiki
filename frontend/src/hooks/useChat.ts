import { useState } from "react";

import { ChatMessage, postChat, ViewContext } from "../api/client";

export function useChat(initialChatId: string | null = null) {
  const [chatId, setChatId] = useState<string | null>(initialChatId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  async function send(text: string, context: ViewContext = null) {
    setMessages((m) => [...m, { role: "user", content: text, tool_steps: [] }]);
    const res = await postChat(text, { chatId: chatId ?? undefined, context });
    setChatId(res.chat_id);
    setMessages((m) => [...m, { role: "assistant", content: res.reply, tool_steps: res.actions }]);
    return res;
  }

  return { chatId, messages, send };
}
