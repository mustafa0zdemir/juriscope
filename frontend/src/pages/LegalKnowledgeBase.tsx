import { useRef, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useLegalKnowledgeBase } from "../hooks/useLegalKnowledgeBase";
import type { LegalDocumentType } from "../types";
import { Badge, Button, EmptyState, Icon, SectionHeader, Skeleton } from "../components/ui";
import { contractStatusLabels, legalDocumentTypeLabels } from "../utils/labels";
import "./LegalKnowledgeBase.css";

const documentTypes: Array<{ value: LegalDocumentType; label: string }> = [
  ...Object.entries(legalDocumentTypeLabels).map(([value, label]) => ({
    value: value as LegalDocumentType,
    label,
  })),
];

export default function LegalKnowledgeBase() {
  const { user } = useAuth();
  const knowledgeBase = useLegalKnowledgeBase(Boolean(user?.is_admin));
  const fileInputRef = useRef<HTMLInputElement>(null);
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
      <SectionHeader eyebrow="Yönetici Alanı" title="Merkezi Hukuk Bilgi Tabanı" description="Kanun, yönetmelik ve emsal kararları merkezi kaynak koleksiyonunda yönetin." action={<Badge tone="info">{knowledgeBase.documents.length} belge</Badge>} />

      {knowledgeBase.error && <div className="legal-kb-error">{knowledgeBase.error}</div>}

      <div className="legal-kb-layout">
        <form className="legal-upload-panel ui-card" onSubmit={(event) => void submit(event)}>
          <div className="kb-panel-title"><span><Icon name="upload" /></span><div><h2>Hukuki belge yükle</h2><p>Merkezi kaynak havuzuna ekleyin</p></div></div>
          <label>Başlık<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
          <label>Belge türü<select value={documentType} onChange={(event) => setDocumentType(event.target.value as LegalDocumentType)}>{documentTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
          <label>Kaynak<input value={source} onChange={(event) => setSource(event.target.value)} required /></label>
          <label>Resmî / karar numarası<input value={officialNumber} onChange={(event) => setOfficialNumber(event.target.value)} /></label>
          <label>Yayın tarihi<input type="date" value={publicationDate} onChange={(event) => setPublicationDate(event.target.value)} /></label>
          <input ref={fileInputRef} hidden type="file" accept=".pdf,.docx" onChange={(event) => { setFile(event.target.files?.[0] ?? null); }} />
          <div className="file-field">
            <span className="file-field-label">PDF veya DOCX</span>
            <button type="button" className="file-pick-btn" onClick={() => fileInputRef.current?.click()}>
              {file ? file.name : "Dosya Seç"}
            </button>
          </div>
          <Button type="submit" icon="plus" disabled={knowledgeBase.isUploading || !file}>{knowledgeBase.isUploading ? "Yükleniyor..." : "Bilgi tabanına ekle"}</Button>
        </form>

        <section className="legal-document-panel ui-card">
          <div className="kb-panel-title"><span><Icon name="book" /></span><div><h2>Belgeler</h2><p>Arayın, filtreleyin ve inceleyin</p></div></div>
          <div className="kb-toolbar"><label><Icon name="search" size={15} /><input aria-label="Hukuki belgelerde ara" placeholder="Başlık, kaynak veya numara ara" value={knowledgeBase.search} onChange={(event) => knowledgeBase.setSearch(event.target.value)} /></label><select aria-label="Belge türüne göre filtrele" value={knowledgeBase.typeFilter} onChange={(event) => knowledgeBase.setTypeFilter(event.target.value)}><option value="ALL">Tüm türler</option>{documentTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></div>
          {knowledgeBase.isLoading ? <Skeleton lines={6} /> : knowledgeBase.visibleDocuments.length === 0 ? <EmptyState icon="search" title="Belge bulunamadı" description="Arama veya filtre kriterlerinizi değiştirin." /> : (
            <div className="legal-document-list">
              {knowledgeBase.visibleDocuments.map((document) => (
                <button type="button" key={document.id} className={knowledgeBase.selectedDocument?.id === document.id ? "active" : ""} onClick={() => knowledgeBase.setSelectedDocument(document)}>
                  <i><Icon name={document.document_type.includes("COURT") ? "shield" : "book"} size={16} /></i><span><strong>{document.title}</strong><small>{legalDocumentTypeLabels[document.document_type]} · {document.source}</small></span><Badge tone={document.status === "embedded" ? "success" : "warning"}>{contractStatusLabels[document.status] ?? document.status}</Badge>
                </button>
              ))}
            </div>
          )}
          <div className="kb-pagination"><button type="button" disabled={knowledgeBase.page <= 1} onClick={() => knowledgeBase.setPage(knowledgeBase.page - 1)}>Önceki</button><span>{knowledgeBase.page} / {knowledgeBase.totalPages}</span><button type="button" disabled={knowledgeBase.page >= knowledgeBase.totalPages} onClick={() => knowledgeBase.setPage(knowledgeBase.page + 1)}>Sonraki</button></div>
        </section>

        <aside className="legal-detail-panel ui-card">
          {knowledgeBase.selectedDocument ? (
            <>
              <p className="eyebrow">BELGE DETAYI</p>
              <h2>{knowledgeBase.selectedDocument.title}</h2>
              <dl>
                <div><dt>Tür</dt><dd>{legalDocumentTypeLabels[knowledgeBase.selectedDocument.document_type]}</dd></div>
                <div><dt>Kaynak</dt><dd>{knowledgeBase.selectedDocument.source}</dd></div>
                <div><dt>Numara</dt><dd>{knowledgeBase.selectedDocument.official_number ?? "—"}</dd></div>
                <div><dt>Yayın</dt><dd>{knowledgeBase.selectedDocument.publication_date ?? "—"}</dd></div>
                <div><dt>Durum</dt><dd>{contractStatusLabels[knowledgeBase.selectedDocument.status] ?? knowledgeBase.selectedDocument.status}</dd></div>
                <div><dt>Dosya</dt><dd>{knowledgeBase.selectedDocument.original_filename}</dd></div>
              </dl>
              <Button variant="danger" icon="trash" onClick={() => {
                if (window.confirm("Bu hukuki belgeyi kalıcı olarak silmek istediğinize emin misiniz?")) {
                  void knowledgeBase.deleteDocument(knowledgeBase.selectedDocument!.id);
                }
              }}>Belgeyi sil</Button>
            </>
          ) : <EmptyState icon="document" title="Belge seçilmedi" description="Detayları görmek için listeden bir kaynak seçin." />}
        </aside>
      </div>
    </div>
  );
}
