import type { FinalAction, SourceInfo } from "./events";

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceInfo[];
  action?: FinalAction;
  /** true while an assistant message is still streaming in (typing effect). */
  pending?: boolean;
}
