import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useLegalKnowledgeBase } from "../hooks/useLegalKnowledgeBase";
import type { LegalDocumentType } from "../types";
import "./LegalKnowledgeBase.css";

const documentTypes: Array<{ value: LegalDocumentType; label: string }> = [
  { value: "LAW", label: "Kanun" },
  { value: "REGULATION", label: "Yönetmelik" },
  { value: "COMMUNIQUE", label: "Tebliğ" },
  { value: "SUPREME_COURT", label: "Yargıtay Kararı" },
  { value: "COUNCIL_OF_STATE", label: "Danıştay Kararı" },
  { value: "CONSTITUTIONAL_COURT", label: "Anayasa Mahkemesi Kararı" },
  { value: "OTHER", label: "Diğer" },
];

export default function LegalKnowledgeBase() {
  const { user } = useAuth();
  const knowledgeBase = useLegalKnowledgeBase(Boolean(user?.is_admin));
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState<LegalDocumentType>("LAW");
  const [source, setSource] = useState("Resmî Gazete");
  const [officialNumber, setOfficialNumber] = useState("");
  const [publicationDate, setPublicationDate] = useState("");

  if (!user?.is_admin) return <Navigate to="/dashboard" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !title.trim() || !source.trim()) return;
    try {
      await knowledgeBase.uploadDocument({
        file,
        title: title.trim(),
        documentType,
        source: source.trim(),
        officialNumber: officialNumber.trim(),
        publicationDate,
      });
      setFile(null);
      setTitle("");
      setOfficialNumber("");
      setPublicationDate("");
    } catch {
      return;
    }
  };

  return (
    <div className="legal-kb-page">
      <header className="legal-kb-header">
        <div>
          <p className="eyebrow">YÖNETİCİ ALANI</p>
          <h1>Legal Knowledge Base</h1>
          <p>Kanunları ve emsal kararları merkezi RAG koleksiyonuna aktarın.</p>
        </div>
        <span>{knowledgeBase.documents.length} belge</span>
      </header>

      {knowledgeBase.error && <div className="legal-kb-error">{knowledgeBase.error}</div>}

      <div className="legal-kb-layout">
        <form className="legal-upload-panel" onSubmit={(event) => void submit(event)}>
          <h2>Legal belge yükle</h2>
          <label>Başlık<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
          <label>Belge türü<select value={documentType} onChange={(event) => setDocumentType(event.target.value as LegalDocumentType)}>{documentTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
          <label>Kaynak<input value={source} onChange={(event) => setSource(event.target.value)} required /></label>
          <label>Resmî / karar numarası<input value={officialNumber} onChange={(event) => setOfficialNumber(event.target.value)} /></label>
          <label>Yayın tarihi<input type="date" value={publicationDate} onChange={(event) => setPublicationDate(event.target.value)} /></label>
          <label>PDF veya DOCX<input type="file" accept=".pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></label>
          <button type="submit" disabled={knowledgeBase.isUploading || !file}>{knowledgeBase.isUploading ? "Yükleniyor..." : "Bilgi tabanına ekle"}</button>
        </form>

        <section className="legal-document-panel">
          <h2>Belgeler</h2>
          {knowledgeBase.isLoading ? <p>Belgeler yükleniyor...</p> : knowledgeBase.documents.length === 0 ? <p>Henüz legal belge bulunmuyor.</p> : (
            <div className="legal-document-list">
              {knowledgeBase.documents.map((document) => (
                <button key={document.id} className={knowledgeBase.selectedDocument?.id === document.id ? "active" : ""} onClick={() => knowledgeBase.setSelectedDocument(document)}>
                  <strong>{document.title}</strong>
                  <span>{documentTypes.find((type) => type.value === document.document_type)?.label}</span>
                  <small>{document.status}</small>
                </button>
              ))}
            </div>
          )}
        </section>

        <aside className="legal-detail-panel">
          {knowledgeBase.selectedDocument ? (
            <>
              <p className="eyebrow">BELGE DETAYI</p>
              <h2>{knowledgeBase.selectedDocument.title}</h2>
              <dl>
                <div><dt>Tür</dt><dd>{knowledgeBase.selectedDocument.document_type}</dd></div>
                <div><dt>Kaynak</dt><dd>{knowledgeBase.selectedDocument.source}</dd></div>
                <div><dt>Numara</dt><dd>{knowledgeBase.selectedDocument.official_number ?? "—"}</dd></div>
                <div><dt>Yayın</dt><dd>{knowledgeBase.selectedDocument.publication_date ?? "—"}</dd></div>
                <div><dt>Durum</dt><dd>{knowledgeBase.selectedDocument.status}</dd></div>
                <div><dt>Dosya</dt><dd>{knowledgeBase.selectedDocument.original_filename}</dd></div>
              </dl>
              <button className="legal-delete-button" onClick={() => void knowledgeBase.deleteDocument(knowledgeBase.selectedDocument!.id)}>Belgeyi sil</button>
            </>
          ) : <p>Detayları görmek için bir belge seçin.</p>}
        </aside>
      </div>
    </div>
  );
}
