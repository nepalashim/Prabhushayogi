import { useState, type FormEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-[var(--border)] p-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about Demat, PMS, IPO, RTS, Mutual Funds..."
        rows={1}
        disabled={disabled}
        className="max-h-24 flex-1 resize-none rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--brand-green)] disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--brand-green)] text-white transition disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M22 2 11 13" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M22 2 15 22l-4-9-9-4 20-7Z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </form>
  );
}
