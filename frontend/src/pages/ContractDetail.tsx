import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useLegalAnalysis } from "../hooks/useLegalAnalysis";
import type { AnalysisFinding, LegalRecommendation, LegalRisk, RiskCategory } from "../types";
import {
  ConfidencePanel,
  EvidencePanel,
  ReasoningPanel,
  RetrievalPathPanel,
} from "../components/analysis/ExplainPanels";
import {
  ClauseExplorer,
  CompliancePanel,
  RiskCategories,
} from "../components/analysis/AdvancedPanels";
import { Badge, Button, Icon, SectionHeader } from "../components/ui";
import { contractStatusLabels, legalDocumentTypeLabels } from "../utils/labels";
import "./ContractDetail.css";

type AnalysisTab =
  | "summary"
  | "risks"
  | "citations"
  | "explain"
  | "evidence"
  | "confidence"
  | "retrieval-path"
  | "clauses"
  | "compliance";

const tabs: Array<{ id: AnalysisTab; label: string }> = [
  { id: "summary", label: "Genel Özet" },
  { id: "risks", label: "Riskler" },
  { id: "explain", label: "Analiz Gerekçesi" },
  { id: "evidence", label: "Hukuki Dayanaklar" },
  { id: "compliance", label: "Mevzuat Uyumu" },
  { id: "clauses", label: "Madde İncelemesi" },
  { id: "citations", label: "Kaynaklar" },
  { id: "confidence", label: "Güven Düzeyi" },
  { id: "retrieval-path", label: "Kaynak Erişim Süreci" },
];

function riskLabel(category: RiskCategory): string {
  if (!category) return "Bilinmeyen";
  const labels: Record<RiskCategory, string> = {
    LOW: "Düşük",
    MEDIUM: "Orta",
    HIGH: "Yüksek",
    CRITICAL: "Kritik",
  };
  return labels[category] || "Bilinmeyen";
}

function RiskRing({ score, category }: { score: number; category: RiskCategory }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const safeCategory = category || "LOW";
  const safeScore = score || 0;
  return <div className={`risk-ring ring-${safeCategory.toLowerCase()}`}><svg viewBox="0 0 100 100" aria-label={`Risk puanı ${safeScore}`}><circle className="risk-ring-track" cx="50" cy="50" r={radius} /><circle className="risk-ring-value" cx="50" cy="50" r={radius} strokeDasharray={circumference} strokeDashoffset={circumference * (1 - safeScore / 100)} /></svg><div><strong>{safeScore}</strong><span>/100</span></div></div>;
}

function FindingList({ findings }: { findings: AnalysisFinding[] }) {
  if (!findings.length) return <p className="analysis-empty">Bu kategoride bulgu tespit edilmedi.</p>;
  return (
    <div className="finding-list">
      {findings.map((finding, index) => (
        <article className="finding-card" key={`${finding.title}-${index}`}>
          <h3>{finding.title}</h3>
          <p>{finding.description}</p>
          {finding.citation && <span>Kaynak {finding.citation}</span>}
        </article>
      ))}
    </div>
  );
}

function RiskList({ risks }: { risks: LegalRisk[] }) {
  if (!risks.length) return <p className="analysis-empty">Önemli bir risk tespit edilmedi.</p>;
  return (
    <div className="finding-list">
      {risks.map((risk, index) => (
        <article className="risk-card" key={`${risk.title}-${index}`}>
          <div className="risk-card-header">
            <h3>{risk.title}</h3>
            <span className={`severity severity-${risk.severity.toLowerCase()}`}>{riskLabel(risk.severity)}</span>
          </div>
          <p>{risk.description}</p>
          <strong>Neden önemli?</strong>
          <p>{risk.reason}</p>
          {risk.citation && <span>Kaynak {risk.citation}</span>}
        </article>
      ))}
    </div>
  );
}

function RecommendationList({ recommendations }: { recommendations: LegalRecommendation[] }) {
  if (!recommendations.length) return <p className="analysis-empty">Şu an için ek öneri bulunmuyor.</p>;
  return (
    <div className="finding-list">
      {recommendations.map((recommendation, index) => (
        <article className="finding-card recommendation-card" key={`${recommendation.title}-${index}`}>
          <h3>{recommendation.title}</h3>
          <p>{recommendation.description}</p>
          {recommendation.related_risk && <span>İlgili risk: {recommendation.related_risk}</span>}
        </article>
      ))}
    </div>
  );
}

export default function ContractDetail() {
  const { contractId } = useParams();
  const numericContractId = contractId ? Number(contractId) : null;
  const {
    contract,
    analysis,
    explanation,
    clauses,
    compliance,
    isLoading,
    isAnalyzing,
    error,
    analyze,
    explain,
    detectClauses,
    checkCompliance,
  } = useLegalAnalysis(
    Number.isInteger(numericContractId) ? numericContractId : null,
  );
  const [activeTab, setActiveTab] = useState<AnalysisTab>("summary");

  if (isLoading) return <div className="contract-loading">Sözleşme yükleniyor...</div>;
  if (!contract) return <div className="contract-loading">{error || "Sözleşme bulunamadı"}</div>;

  const isReady = contract.status === "embedded";

  return (
    <div className="contract-detail-page">
      <Link className="back-link" to="/dashboard">← Genel bakışa dön</Link>
      <SectionHeader eyebrow="Sözleşme Detayı" title={contract.original_filename} description="Belge bilgileri, yapay zekâ destekli hukuki analiz, dayanaklar ve mevzuat uyumu sonuçları." action={<div className="analysis-actions"><Button disabled={!isReady || isAnalyzing} icon="sparkle" onClick={() => void analyze()}>{isAnalyzing ? "Hukuki analiz yapılıyor..." : "Hukuki Analizi Başlat"}</Button><Button variant="secondary" disabled={!isReady || isAnalyzing} icon="shield" onClick={() => void explain().then((succeeded) => succeeded && setActiveTab("explain"))}>Gerekçeli Analiz</Button><Button variant="secondary" disabled={!isReady || isAnalyzing} icon="search" onClick={() => void detectClauses().then((succeeded) => succeeded && setActiveTab("clauses"))}>Maddeleri İncele</Button><Button variant="secondary" disabled={!isReady || isAnalyzing} icon="check" onClick={() => void checkCompliance().then((succeeded) => succeeded && setActiveTab("compliance"))}>Mevzuat Uyumu</Button></div>} />

      <section className="contract-meta-grid" aria-label="Sözleşme bilgileri">
        <div><Icon name="document" /><span>Dosya Bilgisi</span><strong>{contract.mime_type.split("/").at(-1)?.toUpperCase()}</strong></div>
        <div><Icon name="clock" /><span>Yükleme Tarihi</span><strong>{new Date(contract.uploaded_at).toLocaleDateString("tr-TR")}</strong></div>
        <div><Icon name="activity" /><span>Belge Durumu</span><Badge tone={isReady ? "success" : "warning"}>{contractStatusLabels[contract.status] ?? contract.status}</Badge></div>
        <div><Icon name="check" /><span>Vektör Dizinleme</span><strong>{isReady ? "Tamamlandı" : "Bekliyor"}</strong></div>
        <div><Icon name="shield" /><span>Mevzuat Uyumu</span><strong>{compliance ? `${compliance.compliance_score}/100` : "—"}</strong></div>
        <div><Icon name="alert" /><span>Risk</span><strong>{analysis ? `${analysis.risk_score}/100` : "—"}</strong></div>
        <div><Icon name="sparkle" /><span>Analiz Durumu</span><strong>{analysis ? "Tamamlandı" : "Bekliyor"}</strong></div>
        <div><Icon name="download" /><span>Dosya Boyutu</span><strong>{(contract.file_size / 1024).toFixed(1)} KB</strong></div>
      </section>

      {!isReady && <p className="analysis-notice">Sözleşme embedding işlemi tamamlandığında analiz başlatılabilir.</p>}
      {error && <p className="analysis-error">{error}</p>}

      {!analysis && !isAnalyzing && (
        <section className="analysis-placeholder">
          <h2>Hukuki Analiz</h2>
          <p>Risk puanı, eksik maddeler, belirsiz hükümler ve iyileştirme önerileri için analizi başlatın.</p>
        </section>
      )}

      {(analysis || explanation || clauses || compliance) && (
        <section className="analysis-results">
          {analysis && <div className="risk-overview">
            <RiskRing score={analysis.risk_score} category={analysis.risk_category} />
            <div>
              <p className="eyebrow">Risk Puanı</p>
              <h2>{riskLabel(analysis.risk_category)} Risk</h2>
              <p>Analiz güveni: %{Math.round(analysis.confidence * 100)}</p>
            </div>
          </div>}

          <div className="analysis-tabs" role="tablist" aria-label="Analiz bölümleri">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={activeTab === tab.id ? "active" : ""}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                aria-selected={activeTab === tab.id}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="analysis-tab-content">
            {activeTab === "summary" && (analysis ? <div className="analysis-summary-layout"><div className="summary-copy"><h3>Yönetici Özeti</h3><p className="summary-text">{analysis.summary}</p></div><div className="summary-findings"><section><h3>Eksik Maddeler</h3><FindingList findings={analysis.missing_clauses} /></section><section><h3>Belirsiz Maddeler</h3><FindingList findings={analysis.ambiguous_clauses} /></section><section><h3>Tek Taraflı Hükümler</h3><FindingList findings={analysis.one_sided_clauses} /></section></div></div> : <p className="analysis-empty">Temel analiz henüz oluşturulmadı.</p>)}
            {activeTab === "risks" && (analysis ? <div className="risk-tab-layout"><section><h3>Tespit Edilen Riskler</h3><RiskList risks={analysis.risks} /></section><section><h3>Önerilen Aksiyonlar</h3><RecommendationList recommendations={analysis.recommendations} /></section></div> : <p className="analysis-empty">Risk analizi henüz oluşturulmadı.</p>)}
            {activeTab === "citations" && (
              <div className="citation-list">
                {(analysis?.citations ?? []).map((citation, index) => (
                  <article className="citation-card" key={citation.chunk_id}>
                    <div className="source-card-heading"><i><Icon name={citation.source_type === "legal" ? "book" : "document"} size={16} /></i><strong>Kaynak {index + 1}</strong></div>
                    {citation.source_type === "legal" ? (
                      <>
                        <span>{citation.title ?? "Hukuki kaynak"}</span>
                        <span>{citation.court ?? (citation.document_type ? legalDocumentTypeLabels[citation.document_type] : "Hukuki kaynak")}</span>
                        <span>{citation.official_number ?? citation.decision_number ?? "Numara belirtilmemiş"}</span>
                      </>
                    ) : (
                      <span>Sözleşme #{citation.contract_id}</span>
                    )}
                    <span>Sayfa {citation.page ?? citation.page_number ?? "belirtilmemiş"}</span>
                    <span>Skor {citation.score.toFixed(2)}</span>
                    <span>Yeniden sıralama {citation.rerank_score?.toFixed(2) ?? "—"}</span>
                  </article>
                ))}
              </div>
            )}
            {activeTab === "explain" && (explanation
              ? <ReasoningPanel explanation={explanation} />
              : <p className="analysis-empty">Açıklama için “Açıklanabilir Analiz” işlemini başlatın.</p>)}
            {activeTab === "evidence" && (explanation
              ? <EvidencePanel explanation={explanation} />
              : <p className="analysis-empty">Hukuki dayanaklar henüz oluşturulmadı.</p>)}
            {activeTab === "confidence" && (explanation
              ? <ConfidencePanel explanation={explanation} />
              : <p className="analysis-empty">Güven puanı için açıklanabilir analizi başlatın.</p>)}
            {activeTab === "retrieval-path" && (explanation
              ? <RetrievalPathPanel explanation={explanation} />
              : <p className="analysis-empty">Kaynak erişim süreci henüz oluşturulmadı.</p>)}
            {activeTab === "clauses" && (clauses
              ? <ClauseExplorer result={clauses} />
              : <p className="analysis-empty">Madde incelemesi için “Maddeleri İncele” işlemini başlatın.</p>)}
            {activeTab === "compliance" && (compliance
              ? <><CompliancePanel report={compliance} /><div className="risk-category-section"><h3>Risk Kategorileri</h3><RiskCategories tags={compliance.risk_tags} /></div></>
              : <p className="analysis-empty">Mevzuat uyumu raporu için denetimi başlatın.</p>)}
          </div>
        </section>
      )}
    </div>
  );
}
