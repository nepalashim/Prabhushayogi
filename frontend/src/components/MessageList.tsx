import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types/chat";
import { MessageBubble } from "./MessageBubble";
import { StatusIndicator } from "./StatusIndicator";

interface MessageListProps {
  messages: ChatMessage[];
  statusMessage: string | null;
}

export function MessageList({ messages, statusMessage }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, statusMessage]);

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {statusMessage && <StatusIndicator message={statusMessage} />}
      <div ref={bottomRef} />
    </div>
  );
}
