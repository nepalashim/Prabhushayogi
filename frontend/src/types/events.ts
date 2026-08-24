// TypeScript mirrors of the SSE payload shapes app/routes/chat.py sends.
// Event sequence: status* -> answer_chunk* -> sources -> done, or error in
// place of the tail (see the backend's docstring for the full design).

export interface StatusPayload {
  stage: "rewriting" | "retrieving" | "fetching" | "verifying";
  message: string;
}

export interface AnswerChunkPayload {
  text: string;
}

export interface SourceInfo {
  title: string;
  url_or_filename: string;
  doc_type: "webpage" | "pdf";
  chunk_id?: string;
}

export interface SourcesPayload {
  sources: SourceInfo[];
}

export type FinalAction = "answered" | "fallback" | "skipped_smalltalk";

export interface DonePayload {
  action: FinalAction;
  session_id: string;
}

export interface ErrorPayload {
  message: string;
}

export type ChatSSEEvent =
  | { event: "status"; data: StatusPayload }
  | { event: "answer_chunk"; data: AnswerChunkPayload }
  | { event: "sources"; data: SourcesPayload }
  | { event: "done"; data: DonePayload }
  | { event: "error"; data: ErrorPayload };
