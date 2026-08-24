import { Avatar } from "./Avatar";

interface ChatHeaderProps {
  onClose: () => void;
  onBack?: () => void;
}

export function ChatHeader({ onClose, onBack }: ChatHeaderProps) {
  return (
    <div
      className="flex items-center gap-3 rounded-t-2xl px-4 py-3 text-white"
      style={{ background: "linear-gradient(135deg, var(--brand-green), var(--brand-green-dark))" }}
    >
      {onBack && (
        <button type="button" onClick={onBack} aria-label="Back" className="shrink-0 opacity-90 hover:opacity-100">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M15 18 9 12l6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}
      <Avatar size={36} />
      <div className="flex-1 leading-tight">
        <p className="text-sm font-semibold">Prabhu Sahayogi</p>
        <p className="text-[11px] text-white/80">Prabhu Capital Assistant</p>
      </div>
      <button type="button" onClick={onClose} aria-label="Close chat" className="shrink-0 opacity-90 hover:opacity-100">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M6 6l12 12M18 6 6 18" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  );
}
