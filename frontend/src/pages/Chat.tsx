import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "../hooks/useChat";
import type { ChatMessage, Citation } from "../types";
import "./Chat.css";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="citation-card">
      <div className="citation-card-title">Sözleşme #{citation.contract_id}</div>
      <div className="citation-card-meta">
        <span>Sayfa {citation.page_number ?? "—"}</span>
        <span>Chunk {citation.chunk_index}</span>
        <span>Benzerlik {(citation.score * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="typing-indicator" aria-label="Cevap yazılıyor">
      <span />
      <span />
      <span />
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copyAnswer = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <article className={`chat-message ${isUser ? "user-message" : "assistant-message"}`}>
      <div className="message-avatar">{isUser ? "S" : "✦"}</div>
      <div className="message-body">
        <div className="message-heading">
          <strong>{isUser ? "Siz" : "Sözleşme Asistanı"}</strong>
          <time>{formatDate(message.created_at)}</time>
        </div>
        <div className="message-content">
          {isUser ? (
            <p>{message.content}</p>
          ) : message.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          ) : message.isStreaming ? (
            <TypingIndicator />
          ) : (
            <span className="empty-answer">Cevap oluşturulamadı.</span>
          )}
        </div>
        {message.isStreaming && message.content && <span className="streaming-cursor" />}
        {!isUser && message.citations.length > 0 && (
          <div className="citation-list">
            <div className="citation-list-heading">Kaynaklar</div>
            <div className="citation-grid">
              {message.citations.map((citation) => (
                <CitationCard key={`${citation.contract_id}-${citation.chunk_id}`} citation={citation} />
              ))}
            </div>
          </div>
        )}
        {!isUser && message.content && !message.isStreaming && (
          <button type="button" className="copy-button" onClick={copyAnswer}>
            {copied ? "Kopyalandı" : "Cevabı kopyala"}
          </button>
        )}
        {message.error && <div className="message-error">{message.error}</div>}
      </div>
    </article>
  );
}

export default function Chat() {
  const {
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
  } = useChat();
  const [question, setQuestion] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submitQuestion = async (event: FormEvent) => {
    event.preventDefault();
    const value = question.trim();
    if (!value) return;
    setQuestion("");
    await sendMessage(value);
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <div className="chat-page">
      <aside className="conversation-sidebar">
        <div className="sidebar-header">
          <div>
            <span className="eyebrow">ÇALIŞMA ALANI</span>
            <h1>Sohbetler</h1>
          </div>
          <button type="button" className="new-chat-button" onClick={() => void createConversation()}>
            <span>+</span> Yeni
          </button>
        </div>
        <div className="conversation-list">
          {conversations.length === 0 ? (
            <div className="conversation-empty">Henüz sohbet yok. Yeni bir analiz başlatın.</div>
          ) : (
            conversations.map((conversation) => (
              <div
                className={`conversation-row ${activeConversationId === conversation.id ? "active" : ""}`}
                key={conversation.id}
              >
                <button type="button" className="conversation-select" onClick={() => void loadConversation(conversation.id)}>
                  <span className="conversation-icon">◌</span>
                  <span className="conversation-copy">
                    <strong>{conversation.title}</strong>
                    <small>{formatDate(conversation.updated_at)}</small>
                  </span>
                </button>
                <button
                  type="button"
                  className="conversation-delete"
                  aria-label="Sohbeti sil"
                  onClick={() => void deleteConversation(conversation.id)}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <div>
            <span className="eyebrow">RAG ANALİZİ</span>
            <h2>{activeConversationId ? conversations.find((item) => item.id === activeConversationId)?.title ?? "Sohbet" : "Yeni sözleşme sohbeti"}</h2>
          </div>
          <span className="connection-status"><i /> Gemini hazır</span>
        </header>

        <div className="message-list">
          {isLoading ? (
            <div className="chat-loading"><div className="spinner" /> Sohbet yükleniyor...</div>
          ) : messages.length === 0 ? (
            <div className="chat-empty-state">
              <div className="empty-orb">✦</div>
              <h3>Sözleşmelerinizi birlikte inceleyelim</h3>
              <p>Bir sözleşme hakkında soru sorun. Cevapları kaynaklarıyla birlikte ve anlık olarak hazırlayacağım.</p>
              <div className="suggestion-list">
                {['Bu sözleşmenin fesih şartları nelerdir?', 'Tarafların yükümlülüklerini özetle', 'Riskli maddeleri bul'].map((suggestion) => (
                  <button type="button" key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="chat-error">
            <span>{error}</span>
            {!isStreaming && <button type="button" onClick={() => void retryLastMessage()}>Tekrar dene</button>}
          </div>
        )}

        <form className="composer" onSubmit={(event) => void submitQuestion(event)}>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Sözleşmeniz hakkında bir soru sorun..."
            rows={1}
            disabled={isStreaming}
            aria-label="Soru"
          />
          <div className="composer-footer">
            <span>Enter gönderir · Shift + Enter yeni satır</span>
            {isStreaming ? (
              <button type="button" className="stop-button" onClick={stopGeneration}>■ Durdur</button>
            ) : (
              <button type="submit" className="send-button" disabled={!question.trim()}>Gönder <span>↗</span></button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
