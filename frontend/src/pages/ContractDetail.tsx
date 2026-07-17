import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useLegalAnalysis } from "../hooks/useLegalAnalysis";
import type { AnalysisFinding, LegalRecommendation, LegalRisk, RiskCategory } from "../types";
import "./ContractDetail.css";

type AnalysisTab =
  | "summary"
  | "risks"
  | "missing"
  | "ambiguous"
  | "one-sided"
  | "recommendations"
  | "citations";

const tabs: Array<{ id: AnalysisTab; label: string }> = [
  { id: "summary", label: "Genel Özet" },
  { id: "risks", label: "Riskler" },
  { id: "missing", label: "Eksik Maddeler" },
  { id: "ambiguous", label: "Belirsiz Maddeler" },
  { id: "one-sided", label: "Tek Taraflı Maddeler" },
  { id: "recommendations", label: "Öneriler" },
  { id: "citations", label: "Kaynaklar" },
];

function riskLabel(category: RiskCategory): string {
  const labels: Record<RiskCategory, string> = {
    LOW: "Düşük",
    MEDIUM: "Orta",
    HIGH: "Yüksek",
    CRITICAL: "Kritik",
  };
  return labels[category];
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
  const { contract, analysis, isLoading, isAnalyzing, error, analyze } = useLegalAnalysis(
    Number.isInteger(numericContractId) ? numericContractId : null,
  );
  const [activeTab, setActiveTab] = useState<AnalysisTab>("summary");

  if (isLoading) return <div className="contract-loading">Sözleşme yükleniyor...</div>;
  if (!contract) return <div className="contract-loading">{error || "Sözleşme bulunamadı"}</div>;

  const isReady = contract.status === "embedded";

  return (
    <div className="contract-detail-page">
      <Link className="back-link" to="/dashboard">← Dashboard'a dön</Link>
      <header className="contract-detail-header">
        <div>
          <p className="eyebrow">Sözleşme Detayı</p>
          <h1>{contract.original_filename}</h1>
          <span className={`contract-status status-${contract.status}`}>{contract.status}</span>
        </div>
        <button className="analyze-button" disabled={!isReady || isAnalyzing} onClick={() => void analyze()}>
          {isAnalyzing ? "Analiz yapılıyor..." : "Analiz Et"}
        </button>
      </header>

      {!isReady && <p className="analysis-notice">Sözleşme embedding işlemi tamamlandığında analiz başlatılabilir.</p>}
      {error && <p className="analysis-error">{error}</p>}

      {!analysis && !isAnalyzing && (
        <section className="analysis-placeholder">
          <h2>Hukuki Analiz</h2>
          <p>Risk puanı, eksik maddeler, belirsiz hükümler ve iyileştirme önerileri için analizi başlatın.</p>
        </section>
      )}

      {analysis && (
        <section className="analysis-results">
          <div className="risk-overview">
            <div className={`risk-score risk-${analysis.risk_category.toLowerCase()}`}>
              <span>{analysis.risk_score}</span>
              <small>/ 100</small>
            </div>
            <div>
              <p className="eyebrow">Risk Puanı</p>
              <h2>{riskLabel(analysis.risk_category)} Risk</h2>
              <p>Analiz güveni: %{Math.round(analysis.confidence * 100)}</p>
            </div>
          </div>

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
            {activeTab === "summary" && <p className="summary-text">{analysis.summary}</p>}
            {activeTab === "risks" && <RiskList risks={analysis.risks} />}
            {activeTab === "missing" && <FindingList findings={analysis.missing_clauses} />}
            {activeTab === "ambiguous" && <FindingList findings={analysis.ambiguous_clauses} />}
            {activeTab === "one-sided" && <FindingList findings={analysis.one_sided_clauses} />}
            {activeTab === "recommendations" && <RecommendationList recommendations={analysis.recommendations} />}
            {activeTab === "citations" && (
              <div className="citation-list">
                {analysis.citations.map((citation, index) => (
                  <article className="citation-card" key={citation.chunk_id}>
                    <strong>Kaynak {index + 1}</strong>
                    {citation.source_type === "legal" ? (
                      <>
                        <span>{citation.title ?? "Hukuki kaynak"}</span>
                        <span>{citation.court ?? citation.document_type}</span>
                        <span>{citation.official_number ?? citation.decision_number ?? "Numara belirtilmemiş"}</span>
                      </>
                    ) : (
                      <span>Sözleşme #{citation.contract_id}</span>
                    )}
                    <span>Sayfa {citation.page ?? citation.page_number ?? "belirtilmemiş"}</span>
                    <span>Skor {citation.score.toFixed(2)}</span>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
