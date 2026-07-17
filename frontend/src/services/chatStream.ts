import type { ChatQueryRequest, StreamEvent } from "../types";

const API_BASE_URL = "http://localhost:8000/api/v1";

export interface StreamHandlers {
  onEvent: (event: StreamEvent) => void;
}

function parseEvent(block: string): StreamEvent | null {
  const lines = block.split("\n");
  const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n");

  if (!event || !data) return null;

  return {
    event: event as StreamEvent["event"],
    data: JSON.parse(data) as Record<string, unknown>,
  };
}

export async function streamChat(
  request: ChatQueryRequest,
  signal: AbortSignal,
  handlers: StreamHandlers,
): Promise<void> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token ?? ""}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Streaming başlatılamadı");
  }

  if (!response.body) throw new Error("Streaming bağlantısı kurulamadı");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const event = parseEvent(block);
      if (event) handlers.onEvent(event);
    }

    if (done) break;
  }

  const lastEvent = parseEvent(buffer);
  if (lastEvent) handlers.onEvent(lastEvent);
}
