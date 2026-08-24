import { useState } from "react";
import { useChatStream } from "../hooks/useChatStream";
import { Avatar } from "./Avatar";
import { CategoryGrid } from "./CategoryGrid";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { DisclaimerFooter } from "./DisclaimerFooter";
import { MessageList } from "./MessageList";

type View = "menu" | "chat";

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  // "menu" (greeting + category grid) vs "chat" (message history) - the "<"
  // header button navigates between these while the conversation persists in
  // the background either way; "X" is the only thing that closes the widget.
  const [view, setView] = useState<View>("menu");
  const { messages, statusMessage, isSending, error, sendMessage } = useChatStream();

  const handleSend = (text: string) => {
    setView("chat");
    sendMessage(text);
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label="Open Prabhu Sahayogi chat"
        className="fixed right-5 bottom-5 flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition hover:scale-105"
        style={{ background: "linear-gradient(135deg, var(--brand-green), var(--brand-green-dark))" }}
      >
        <Avatar size={40} />
      </button>
    );
  }

  return (
    <div className="fixed right-5 bottom-5 flex h-[600px] w-[380px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl">
      <ChatHeader onClose={() => setIsOpen(false)} onBack={view === "chat" ? () => setView("menu") : undefined} />

      {view === "menu" ? (
        <div className="flex-1 overflow-y-auto">
          <p className="px-4 pt-4 text-sm text-[var(--text-primary)]">
            👋 Hi! I&apos;m Prabhu Sahayogi, your virtual assistant for Prabhu Capital&apos;s Demat, PMS, IPO, RTS
            and Mutual Fund services.
          </p>
          <CategoryGrid onSelect={handleSend} />
        </div>
      ) : (
        <MessageList messages={messages} statusMessage={statusMessage} />
      )}

      {error && <p className="px-4 pb-1 text-xs text-[var(--brand-red)]">{error}</p>}

      <ChatInput onSend={handleSend} disabled={isSending} />
      <DisclaimerFooter />
    </div>
  );
}
