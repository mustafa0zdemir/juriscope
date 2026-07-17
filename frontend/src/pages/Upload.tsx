import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Link } from "react-router-dom";
import { Button, Card, Icon, SectionHeader } from "../components/ui";
import { useContractUpload } from "../hooks/useContractUpload";
import "./Upload.css";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export default function Upload() {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploader = useContractUpload();
  const select = (file?: File) => { if (file) void uploader.upload(file); };
  const drop = (event: DragEvent) => { event.preventDefault(); setIsDragging(false); select(event.dataTransfer.files[0]); };
  const change = (event: ChangeEvent<HTMLInputElement>) => select(event.target.files?.[0]);

  return <div className="upload-page">
    <SectionHeader eyebrow="Doküman Yönetimi" title="Yeni sözleşme yükle" description="Sözleşmenizi güvenli belge pipeline’ına aktarın. Metin çıkarma, chunking ve embedding işlemleri otomatik başlar." />
    <div className="upload-layout">
      <Card className="upload-main-card">
        <button className={`upload-dropzone ${isDragging ? "dragging" : ""}`} disabled={uploader.isUploading} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }} onDragLeave={(event) => { event.preventDefault(); setIsDragging(false); }} onDrop={drop} type="button">
          <input ref={inputRef} hidden type="file" accept=".pdf,.doc,.docx,.txt" onChange={change} />
          {uploader.isUploading ? <><div className="spinner" /><h2>Belge güvenli şekilde yükleniyor</h2><p>Lütfen pencereyi kapatmayın.</p></> : <><span className="upload-illustration"><Icon name="upload" size={26} /></span><h2>Dosyayı buraya sürükleyin</h2><p>veya bilgisayarınızdan seçmek için tıklayın</p><span className="upload-formats">PDF · DOC · DOCX · TXT &nbsp; / &nbsp; Maksimum 50 MB</span></>}
        </button>
        {uploader.error && <div className="upload-error"><Icon name="alert" />{uploader.error}</div>}
        {uploader.result && <div className="upload-result"><span><Icon name="check" /></span><div><h3>{uploader.result.message}</h3><p>{uploader.result.filename} · {formatFileSize(uploader.result.size)} · {uploader.result.content_type}</p></div><Link to="/dashboard"><Button variant="secondary">Dashboard'a dön</Button></Link></div>}
      </Card>
      <aside className="upload-guide">
        <Card><span className="guide-icon"><Icon name="shield" /></span><h3>Güvenli işleme</h3><p>Dosyalarınız izole kullanıcı alanında saklanır ve yalnızca yetkili hesabınız tarafından erişilir.</p></Card>
        <Card><span className="guide-icon"><Icon name="activity" /></span><h3>Otomatik pipeline</h3><ol><li><i>1</i>Metin çıkarma</li><li><i>2</i>Akıllı chunking</li><li><i>3</i>Embedding ve indeksleme</li><li><i>4</i>Analize hazır</li></ol></Card>
      </aside>
    </div>
  </div>;
}
