// Shown while the workflow runs, before any (vetted) answer text arrives -
// see the backend's streaming/judge-gate design: status events never carry
// unverified content, so this is always safe to show as-is.
export function StatusIndicator({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-2xl bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--text-muted)] shadow-sm">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--brand-green)] [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--brand-green)] [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--brand-green)]" />
      </span>
      {message}
    </div>
  );
}
