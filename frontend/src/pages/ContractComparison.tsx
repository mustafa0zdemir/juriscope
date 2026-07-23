import { Link } from "react-router-dom";
import { useContractComparison } from "../hooks/useContractComparison";
import type { DetectedClause } from "../types";
import { Badge, Button, Card, Icon, SectionHeader } from "../components/ui";
import { clauseTypeLabels, riskTagLabels } from "../utils/labels";
import "./ContractComparison.css";

function ClauseColumn({ title, clauses, tone }: { title: string; clauses: DetectedClause[]; tone: string }) {
  return (
    <section className={`comparison-column ${tone}`}>
      <h2>{title} <span>{clauses.length}</span></h2>
      {clauses.map((clause) => (
        <article key={`${clause.contract_id}-${clause.clause_type}`}>
          <strong>{clause.title}</strong>
          <p>{clause.text}</p>
          <small>Metin bölümü {clause.chunk_index} · %{Math.round(clause.confidence * 100)} güven</small>
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
      <Link className="back-link" to="/dashboard">← Genel bakışa dön</Link>
      <SectionHeader eyebrow="Gelişmiş Analiz" title="Sözleşme Karşılaştırma" description="İki sürüm arasındaki madde, risk, hak ve yükümlülük değişimlerini inceleyin." />
      <section className="comparison-form">
        <label>Temel sözleşme<select value={comparison.baseId ?? ""} onChange={(event) => {
          const val = Number(event.target.value);
          comparison.setBaseId(val);
          if (val === comparison.comparisonId) {
            const next = comparison.contracts.find((c) => c.id !== val);
            if (next) comparison.setComparisonId(next.id);
          }
        }}>{comparison.contracts.map((contract) => <option value={contract.id} key={contract.id}>{contract.original_filename}</option>)}</select></label>
        <span><Icon name="arrow" /></span>
        <label>Karşılaştırılacak sözleşme<select value={comparison.comparisonId ?? ""} onChange={(event) => {
          const val = Number(event.target.value);
          comparison.setComparisonId(val);
          if (val === comparison.baseId) {
            const next = comparison.contracts.find((c) => c.id !== val);
            if (next) comparison.setBaseId(next.id);
          }
        }}>{comparison.contracts.map((contract) => <option value={contract.id} key={contract.id}>{contract.original_filename}</option>)}</select></label>
        <Button icon="compare" disabled={!comparison.baseId || !comparison.comparisonId || comparison.baseId === comparison.comparisonId || comparison.isComparing} onClick={() => void comparison.compare()}>{comparison.isComparing ? "Karşılaştırılıyor..." : "Karşılaştır"}</Button>
      </section>
      {comparison.error && <p className="analysis-error">{comparison.error}</p>}
      {comparison.contracts.length < 2 && <p className="analysis-notice">Karşılaştırma için en az iki analize hazır sözleşme gerekir.</p>}
      {comparison.result && (
        <section className="comparison-results">
          <div className="comparison-summary"><strong>{comparison.result.summary}</strong><Badge>{comparison.result.unchanged_clauses.length} değişmeyen kategori</Badge></div>
          <div className="comparison-grid">
            <ClauseColumn title="Eklenen Maddeler" clauses={comparison.result.added_clauses} tone="added" />
            <ClauseColumn title="Silinen Maddeler" clauses={comparison.result.removed_clauses} tone="removed" />
          </div>
          <section className="modified-list"><h2>Değiştirilen Maddeler</h2>{comparison.result.modified_clauses.map((change) => <article key={change.clause_type}><strong>{change.before?.title ?? change.clause_type}</strong><span>%{Math.round(change.similarity * 100)} benzerlik</span><p>{change.summary}</p><div><p>{change.before?.text}</p><p>{change.after?.text}</p></div></article>)}</section>
          
          {comparison.result.risk_changes && comparison.result.risk_changes.length > 0 && (
            <section className="risk-changes-list">
              <h2>Risk Değişimleri</h2>
              <div className="risk-changes-grid">
                {comparison.result.risk_changes.map((change, index) => {
                  const directionLabels: Record<string, { label: string; tone: "danger" | "success" | "warning" | "info" | "neutral" }> = {
                    INCREASE: { label: "Risk Artışı", tone: "danger" },
                    DECREASE: { label: "Risk Azalışı", tone: "success" },
                    NEW: { label: "Yeni Risk", tone: "warning" },
                    RESOLVED: { label: "Risk Giderildi", tone: "success" },
                    UNCHANGED: { label: "Risk Değişmedi", tone: "neutral" }
                  };
                  const status = directionLabels[change.direction.toUpperCase()] || { label: change.direction, tone: "neutral" };
                  return (
                    <Card key={index} className="risk-change-card">
                      <div className="risk-change-header">
                        <h3>{clauseTypeLabels[change.clause_type] || change.clause_type}</h3>
                        <Badge tone={status.tone}>{status.label}</Badge>
                      </div>
                      <div className="risk-change-body">
                        <div className="risk-change-side">
                          <span className="side-label">Önceki:</span>
                          <div className="side-tags">
                            {change.before_tags.length > 0 ? (
                              change.before_tags.map((tag) => <Badge key={tag} tone="neutral">{riskTagLabels[tag] || tag}</Badge>)
                            ) : (
                              <span className="no-tags">Yok</span>
                            )}
                          </div>
                        </div>
                        <Icon name="arrow" />
                        <div className="risk-change-side">
                          <span className="side-label">Sonraki:</span>
                          <div className="side-tags">
                            {change.after_tags.length > 0 ? (
                              change.after_tags.map((tag) => <Badge key={tag} tone="neutral">{riskTagLabels[tag] || tag}</Badge>)
                            ) : (
                              <span className="no-tags">Yok</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </section>
          )}

          <div className="comparison-grid compact"><section><h2>Yeni Yükümlülükler</h2>{comparison.result.new_obligations.map((item) => <p key={item}>{item}</p>)}</section><section><h2>Yeni Haklar</h2>{comparison.result.new_rights.map((item) => <p key={item}>{item}</p>)}</section></div>
        </section>
      )}
    </div>
  );
}
