import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import { useSearchParams } from "react-router-dom";
import remarkGfm from "remark-gfm";
import { useChat } from "../hooks/useChat";
import type { ChatMessage, Citation } from "../types";
import { Button, Icon } from "../components/ui";
import { legalDocumentTypeLabels } from "../utils/labels";
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
  const isLegal = citation.source_type === "legal";
  return (
    <div className="citation-card">
      <div className={`citation-source-icon source-${isLegal ? "legal" : "contract"}`}><Icon name={isLegal ? "book" : "document"} size={16} /></div>
      <div className="citation-card-content"><div className="citation-card-title">
        {isLegal ? citation.title ?? "Hukuki kaynak" : `Sözleşme #${citation.contract_id}`}
      </div>
      <div className="citation-card-meta">
        {isLegal && citation.document_type && <span>{legalDocumentTypeLabels[citation.document_type]}</span>}
        {isLegal && citation.official_number && <span>No: {citation.official_number}</span>}
        {isLegal && citation.article && <span>Madde {citation.article}</span>}
        <span>Sayfa {citation.page ?? citation.page_number ?? "—"}</span>
        {!isLegal && <span>Metin bölümü {citation.chunk_index}</span>}
        <span>Benzerlik {(citation.score * 100).toFixed(1)}%</span>
        <span>Yeniden sıralama {citation.rerank_score?.toFixed(2) ?? "—"}</span>
      </div>
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
      <div className="message-avatar">{isUser ? <Icon name="user" size={15} /> : <Icon name="sparkle" size={15} />}</div>
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
                <CitationCard key={`${citation.source_type}-${citation.document_id ?? citation.contract_id}-${citation.chunk_id}`} citation={citation} />
              ))}
            </div>
          </div>
        )}
        {!isUser && message.content && !message.isStreaming && (
          <button type="button" className="copy-button" onClick={copyAnswer}>
            <Icon name={copied ? "check" : "copy"} size={14} />{copied ? "Kopyalandı" : "Kopyala"}
          </button>
        )}
        {message.error && <div className="message-error">{message.error}</div>}
      </div>
    </article>
  );
}

export default function Chat() {
  const [searchParams] = useSearchParams();
  const requestedConversation = Number(searchParams.get("conversation"));
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
  } = useChat(Number.isInteger(requestedConversation) && requestedConversation > 0 ? requestedConversation : null);
  const [question, setQuestion] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
  }, [question]);

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
          <Button type="button" icon="plus" onClick={() => void createConversation()}>Yeni</Button>
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
                  <span className="conversation-icon"><Icon name="chat" size={16} /></span>
                  <span className="conversation-copy">
                    <strong>{conversation.title}</strong>
                    <small>{formatDate(conversation.updated_at)}</small>
                  </span>
                </button>
                <button
                  type="button"
                  className="conversation-delete"
                  aria-label="Sohbeti sil"
                  onClick={() => {
                    if (window.confirm("Bu sohbeti ve tüm mesajlarını silmek istediğinize emin misiniz?")) {
                      void deleteConversation(conversation.id);
                    }
                  }}
                >
                  <Icon name="trash" size={15} />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <div>
            <span className="eyebrow">KAYNAKLANDIRILMIŞ HUKUKİ ANALİZ</span>
            <h2>{activeConversationId ? conversations.find((item) => item.id === activeConversationId)?.title ?? "Sohbet" : "Yeni sözleşme sohbeti"}</h2>
          </div>
          <span className="connection-status"><i /> Gemini · Güvenli RAG</span>
        </header>

        <div className="message-list">
          {isLoading ? (
            <div className="chat-loading"><div className="spinner" /> Sohbet yükleniyor...</div>
          ) : messages.length === 0 ? (
            <div className="chat-empty-state">
              <div className="empty-orb"><Icon name="sparkle" size={24} /></div>
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
            {!isStreaming && <Button type="button" variant="ghost" onClick={() => void retryLastMessage()}>Tekrar dene</Button>}
          </div>
        )}

        <form className="composer" onSubmit={(event) => void submitQuestion(event)}>
          <textarea
            ref={textareaRef}
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
              <Button type="button" variant="danger" icon="x" onClick={stopGeneration}>Üretimi durdur</Button>
            ) : (
              <Button type="submit" icon="send" disabled={!question.trim()}>Gönder</Button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
