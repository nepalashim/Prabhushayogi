import type { ChatSSEEvent } from "../types/events";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

interface ChatStreamRequest {
  sessionId: string;
  message: string;
}

/**
 * POSTs to /api/chat/stream and yields parsed SSE events as they arrive.
 * Native EventSource can't send a POST body, so this reads the response
 * body's ReadableStream directly and parses the SSE wire format by hand.
 */
export async function* streamChat({ sessionId, message }: ChatStreamRequest): AsyncGenerator<ChatSSEEvent> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // sse-starlette sends frames with \r\n line endings (confirmed by
    // inspecting the raw stream) - normalize before splitting, or a plain
    // "\n\n" split never matches and every event silently vanishes into an
    // ever-growing buffer instead of ever being yielded.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? ""; // the last piece may be incomplete - keep it buffered

    for (const frame of frames) {
      const parsed = parseFrame(frame);
      if (parsed) yield parsed;
    }
  }
}

/** A frame with no `event:`/`data:` lines (e.g. sse-starlette's `: ping` keepalive comments) is ignored. */
function parseFrame(frame: string): ChatSSEEvent | null {
  let eventName = "";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (!eventName || dataLines.length === 0) return null;

  const data = JSON.parse(dataLines.join("\n"));
  return { event: eventName, data } as ChatSSEEvent;
}
