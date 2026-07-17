import { useCallback, useEffect, useRef, useState } from "react";
import api from "../services/api";
import { streamChat } from "../services/chatStream";
import type {
  ChatMessage,
  Citation,
  Conversation,
  StreamEvent,
} from "../types";

interface UseChatResult {
  conversations: Conversation[];
  messages: ChatMessage[];
  activeConversationId: number | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: string;
  loadConversation: (conversationId: number) => Promise<void>;
  createConversation: () => Promise<void>;
  deleteConversation: (conversationId: number) => Promise<void>;
  sendMessage: (question: string) => Promise<void>;
  retryLastMessage: () => Promise<void>;
  stopGeneration: () => void;
}

const emptyError = "";

export function useChat(): UseChatResult {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(emptyError);
  const [lastQuestion, setLastQuestion] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadConversations = useCallback(async () => {
    const response = await api.get<Conversation[]>("/conversations");
    setConversations(response.data);
    return response.data;
  }, []);

  const loadConversation = useCallback(async (conversationId: number) => {
    setError(emptyError);
    setIsLoading(true);
    try {
      const response = await api.get<ChatMessage[]>(
        `/conversations/${conversationId}/messages`,
      );
      setActiveConversationId(conversationId);
      setMessages(response.data);
    } catch {
      setError("Sohbet geçmişi yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadConversations()
      .then((items) => {
        if (items.length > 0) void loadConversation(items[0].id);
      })
      .catch(() => setError("Sohbetler yüklenemedi"))
      .finally(() => setIsLoading(false));
  }, [loadConversation, loadConversations]);

  const createConversation = useCallback(async () => {
    setError(emptyError);
    try {
      const response = await api.post<Conversation>("/conversations", {
        title: "Yeni Sohbet",
      });
      setConversations((current) => [response.data, ...current]);
      setActiveConversationId(response.data.id);
      setMessages([]);
    } catch {
      setError("Yeni sohbet oluşturulamadı");
    }
  }, []);

  const deleteConversation = useCallback(async (conversationId: number) => {
    try {
      await api.delete(`/conversations/${conversationId}`);
      const remaining = conversations.filter((item) => item.id !== conversationId);
      setConversations(remaining);
      if (activeConversationId === conversationId) {
        setActiveConversationId(remaining[0]?.id ?? null);
        setMessages([]);
        if (remaining[0]) void loadConversation(remaining[0].id);
      }
    } catch {
      setError("Sohbet silinemedi");
    }
  }, [activeConversationId, conversations, loadConversation]);

  const handleStreamEvent = useCallback((event: StreamEvent) => {
    if (event.event === "start") {
      const conversationId = event.data.conversation_id;
      if (typeof conversationId === "number") {
        setActiveConversationId(conversationId);
      }
    }

    if (event.event === "token") {
      const text = event.data.text;
      if (typeof text !== "string") return;
      setMessages((current) => {
        const last = current[current.length - 1];
        if (!last || last.role !== "assistant") return current;
        return [
          ...current.slice(0, -1),
          { ...last, content: last.content + text, isStreaming: true },
        ];
      });
    }

    if (event.event === "citations") {
      const citations = event.data.citations;
      if (!Array.isArray(citations)) return;
      setMessages((current) => {
        const last = current[current.length - 1];
        if (!last || last.role !== "assistant") return current;
        return [...current.slice(0, -1), { ...last, citations: citations as Citation[] }];
      });
    }

    if (event.event === "guardrails") {
      const message = event.data.message;
      setMessages((current) => {
        const last = current[current.length - 1];
        if (!last || last.role !== "assistant") return current;
        return [
          ...current.slice(0, -1),
          {
            ...last,
            content: typeof message === "string" ? message : "Güvenilir cevap için yeterli context bulunamadı.",
            isStreaming: false,
          },
        ];
      });
    }

    if (event.event === "done") {
      setMessages((current) => {
        const last = current[current.length - 1];
        if (!last || last.role !== "assistant") return current;
        return [
          ...current.slice(0, -1),
          {
            ...last,
            isStreaming: false,
            model: typeof event.data.model === "string" ? event.data.model : last.model,
            latency_ms: typeof event.data.latency_ms === "number" ? event.data.latency_ms : last.latency_ms,
          },
        ];
      });
    }

    if (event.event === "error") {
      const message = event.data.message;
      setError(typeof message === "string" ? message : "Cevap üretilirken hata oluştu");
      setMessages((current) => {
        const last = current[current.length - 1];
        if (!last || last.role !== "assistant") return current;
        return [...current.slice(0, -1), { ...last, isStreaming: false, error: "Cevap tamamlanamadı" }];
      });
    }
  }, []);

  const sendMessage = useCallback(async (question: string) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isStreaming) return;

    setError(emptyError);
    setLastQuestion(trimmedQuestion);
    setIsStreaming(true);
    const assistantId = -Date.now();
    const conversationId = activeConversationId ?? undefined;
    setMessages((current) => [
      ...current,
      {
        id: assistantId - 1,
        conversation_id: conversationId ?? 0,
        role: "user",
        content: trimmedQuestion,
        model: null,
        latency_ms: null,
        citations: [],
        created_at: new Date().toISOString(),
      },
      {
        id: assistantId,
        conversation_id: conversationId ?? 0,
        role: "assistant",
        content: "",
        model: null,
        latency_ms: null,
        citations: [],
        created_at: new Date().toISOString(),
        isStreaming: true,
      },
    ]);

    const controller = new AbortController();
    abortControllerRef.current = controller;
    try {
      await streamChat(
        { question: trimmedQuestion, conversation_id: conversationId, top_k: 5 },
        controller.signal,
        { onEvent: handleStreamEvent },
      );
      await loadConversations();
    } catch (streamError) {
      if (!(streamError instanceof DOMException && streamError.name === "AbortError")) {
        setError(streamError instanceof Error ? streamError.message : "Streaming başarısız oldu");
      }
      setMessages((current) => {
        const last = current[current.length - 1];
        if (!last || last.role !== "assistant") return current;
        return [...current.slice(0, -1), { ...last, isStreaming: false }];
      });
    } finally {
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  }, [activeConversationId, handleStreamEvent, isStreaming, loadConversations]);

  const retryLastMessage = useCallback(async () => {
    if (lastQuestion) {
      setMessages((current) => current.slice(0, -2));
      await sendMessage(lastQuestion);
    }
  }, [lastQuestion, sendMessage]);

  const stopGeneration = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
    setMessages((current) => {
      const last = current[current.length - 1];
      if (!last || last.role !== "assistant") return current;
      return [...current.slice(0, -1), { ...last, isStreaming: false, error: "Üretim durduruldu" }];
    });
  }, []);

  return {
    conversations,
    messages,
    activeConversationId,
    isLoading,
    isStreaming,
    error,
    loadConversation,
    createConversation,
    deleteConversation,
    sendMessage,
    retryLastMessage,
    stopGeneration,
  };
}
