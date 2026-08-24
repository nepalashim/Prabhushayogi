import { useCallback, useState } from "react";
import { streamChat } from "../api/chatStream";
import { getOrCreateSessionId } from "../state/session";
import type { ChatMessage } from "../types/chat";

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      setError(null);
      const sessionId = getOrCreateSessionId();

      const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: trimmed };
      const assistantId = crypto.randomUUID();
      const assistantPlaceholder: ChatMessage = { id: assistantId, role: "assistant", content: "", pending: true };

      setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
      setIsSending(true);
      setStatusMessage(null);

      const applyToAssistant = (update: (m: ChatMessage) => ChatMessage) => {
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? update(m) : m)));
      };

      try {
        for await (const event of streamChat({ sessionId, message: trimmed })) {
          switch (event.event) {
            case "status":
              setStatusMessage(event.data.message);
              break;
            case "answer_chunk":
              setStatusMessage(null);
              applyToAssistant((m) => ({ ...m, content: m.content + event.data.text }));
              break;
            case "sources":
              applyToAssistant((m) => ({ ...m, sources: event.data.sources }));
              break;
            case "done":
              applyToAssistant((m) => ({ ...m, pending: false, action: event.data.action }));
              break;
            case "error":
              setError(event.data.message);
              applyToAssistant((m) => ({ ...m, pending: false, content: m.content || "Something went wrong." }));
              break;
          }
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Something went wrong while contacting the server.";
        setError(message);
        applyToAssistant((m) => ({ ...m, pending: false, content: m.content || message }));
      } finally {
        setIsSending(false);
        setStatusMessage(null);
      }
    },
    [isSending],
  );

  return { messages, statusMessage, isSending, error, sendMessage };
}
