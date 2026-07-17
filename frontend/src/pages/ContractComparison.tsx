import { Link } from "react-router-dom";
import { useContractComparison } from "../hooks/useContractComparison";
import type { DetectedClause } from "../types";
import "./ContractComparison.css";

function ClauseColumn({ title, clauses, tone }: { title: string; clauses: DetectedClause[]; tone: string }) {
  return (
    <section className={`comparison-column ${tone}`}>
      <h2>{title} <span>{clauses.length}</span></h2>
      {clauses.map((clause) => (
        <article key={`${clause.contract_id}-${clause.clause_type}`}>
          <strong>{clause.title}</strong>
          <p>{clause.text}</p>
          <small>Chunk {clause.chunk_index} · %{Math.round(clause.confidence * 100)} güven</small>
        </article>
      ))}
      {!clauses.length && <p className="analysis-empty">Değişiklik bulunamadı.</p>}
    </section>
  );
}

export default function ContractComparison() {
  const comparison = useContractComparison();

  if (comparison.isLoading) return <div className="contract-loading">Sözleşmeler yükleniyor...</div>;

  return (
    <div className="comparison-page">
      <Link className="back-link" to="/dashboard">← Dashboard'a dön</Link>
      <header><p className="eyebrow">Gelişmiş Analiz</p><h1>Sözleşme Karşılaştırma</h1><p>İki sürüm arasındaki madde, risk, hak ve yükümlülük değişimlerini inceleyin.</p></header>
      <section className="comparison-form">
        <label>Temel sözleşme<select value={comparison.baseId ?? ""} onChange={(event) => comparison.setBaseId(Number(event.target.value))}>{comparison.contracts.map((contract) => <option value={contract.id} key={contract.id}>{contract.original_filename}</option>)}</select></label>
        <span>→</span>
        <label>Karşılaştırılacak sözleşme<select value={comparison.comparisonId ?? ""} onChange={(event) => comparison.setComparisonId(Number(event.target.value))}>{comparison.contracts.map((contract) => <option value={contract.id} key={contract.id}>{contract.original_filename}</option>)}</select></label>
        <button disabled={!comparison.baseId || !comparison.comparisonId || comparison.baseId === comparison.comparisonId || comparison.isComparing} onClick={() => void comparison.compare()}>{comparison.isComparing ? "Karşılaştırılıyor..." : "Karşılaştır"}</button>
      </section>
      {comparison.error && <p className="analysis-error">{comparison.error}</p>}
      {comparison.contracts.length < 2 && <p className="analysis-notice">Karşılaştırma için en az iki analize hazır sözleşme gerekir.</p>}
      {comparison.result && (
        <section className="comparison-results">
          <div className="comparison-summary"><strong>{comparison.result.summary}</strong><span>{comparison.result.unchanged_clauses.length} değişmeyen kategori</span></div>
          <div className="comparison-grid">
            <ClauseColumn title="Eklenen Maddeler" clauses={comparison.result.added_clauses} tone="added" />
            <ClauseColumn title="Silinen Maddeler" clauses={comparison.result.removed_clauses} tone="removed" />
          </div>
          <section className="modified-list"><h2>Değiştirilen Maddeler</h2>{comparison.result.modified_clauses.map((change) => <article key={change.clause_type}><strong>{change.before?.title ?? change.clause_type}</strong><span>%{Math.round(change.similarity * 100)} benzerlik</span><p>{change.summary}</p><div><p>{change.before?.text}</p><p>{change.after?.text}</p></div></article>)}</section>
          <div className="comparison-grid compact"><section><h2>Yeni Yükümlülükler</h2>{comparison.result.new_obligations.map((item) => <p key={item}>{item}</p>)}</section><section><h2>Yeni Haklar</h2>{comparison.result.new_rights.map((item) => <p key={item}>{item}</p>)}</section></div>
        </section>
      )}
    </div>
  );
}
