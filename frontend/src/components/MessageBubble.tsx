import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types/chat";
import { SourceChips } from "./SourceChips";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
          isUser
            ? "rounded-br-sm bg-[var(--brand-green)] text-white"
            : "rounded-bl-sm border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)]"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          <div className="prose-chat">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : message.pending ? (
          <span className="text-[var(--text-muted)]">...</span>
        ) : null}

        {!isUser && message.sources && message.sources.length > 0 && <SourceChips sources={message.sources} />}
      </div>
    </div>
  );
}
