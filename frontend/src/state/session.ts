// Session-scoped conversation identity. The backend reconstructs chat
// history server-side from this session_id (query_logging.get_recent_turns)
// - the client only needs to keep sending the same id, which survives a page
// refresh via sessionStorage but resets in a new tab/window, matching a
// normal chat-widget session lifetime.

const SESSION_STORAGE_KEY = "prabhu-sahayogi-session-id";

export function getOrCreateSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const id = crypto.randomUUID();
  sessionStorage.setItem(SESSION_STORAGE_KEY, id);
  return id;
}
