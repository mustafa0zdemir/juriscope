import type { ClauseListResponse, ComplianceReport, RiskTag } from "../../types";
import { clauseTypeLabels, riskTagLabels } from "../../utils/labels";

const complianceLabels = {
  COMPLIANT: "Uygun",
  PARTIAL: "Kısmen Uygun",
  NON_COMPLIANT: "Uygun Değil",
  NOT_APPLICABLE: "Kapsam Dışı",
} as const;

export function ClauseExplorer({ result }: { result: ClauseListResponse }) {
  return (
    <div>
      <div className="analysis-metrics">
        <span><strong>{result.detected_types.length}</strong> kategori tespit edildi</span>
        <span><strong>{result.missing_types.length}</strong> kategori bulunamadı</span>
      </div>
      <div className="finding-list">
        {result.clauses.map((clause) => (
          <article className="clause-card" key={`${clause.chunk_id}-${clause.clause_type}`}>
            <div className="risk-card-header">
              <h3>{clause.title}</h3>
              <span className="clause-confidence">%{Math.round(clause.confidence * 100)}</span>
            </div>
            <p>{clause.text}</p>
            <div className="tag-row">
              {clause.risk_tags.map((tag) => <span key={tag}>{riskTagLabels[tag]}</span>)}
            </div>
            <small>Sayfa {clause.page_number ?? "—"} · Metin bölümü {clause.chunk_index}</small>
          </article>
        ))}
      </div>
    </div>
  );
}

export function CompliancePanel({ report }: { report: ComplianceReport }) {
  return (
    <div>
      <div className="compliance-overview">
        <strong>{report.compliance_score}/100</strong>
        <div><span>{complianceLabels[report.status]}</span><p>{report.disclaimer}</p></div>
      </div>
      <div className="finding-list">
        {report.findings.map((finding) => (
          <article className="compliance-card" key={finding.law}>
            <div className="risk-card-header"><h3>{finding.law}</h3><span>{complianceLabels[finding.status]}</span></div>
            {finding.status === "NOT_APPLICABLE" ? (
              <p>Bu mevzuatın uygulanmasını gerektiren bir sözleşme ilişkisi tespit edilmedi.</p>
            ) : (finding.missing_clauses.length > 0 || finding.issues.length > 0) ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", margin: "0.5rem 0" }}>
                {finding.missing_clauses.length > 0 && (
                  <div>
                    <strong style={{ fontSize: "0.8rem", color: "var(--text-primary)" }}>Eksik Maddeler:</strong>
                    <ul style={{ margin: "0.25rem 0", paddingLeft: "1.2rem" }}>
                      {finding.missing_clauses.map((clause) => (
                        <li key={clause} style={{ fontSize: "0.84rem", color: "var(--text-secondary)" }}>
                          {clauseTypeLabels[clause] || clause} maddesi tespit edilemedi.
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {finding.issues.length > 0 && (
                  <div>
                    <strong style={{ fontSize: "0.8rem", color: "var(--text-primary)" }}>Uyumsuzluk Sorunları:</strong>
                    <ul style={{ margin: "0.25rem 0", paddingLeft: "1.2rem" }}>
                      {finding.issues.map((issue, idx) => (
                        <li key={idx} style={{ fontSize: "0.84rem", color: "var(--text-secondary)" }}>
                          {issue}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p>Temel madde kategorilerinin tamamı tespit edildi.</p>
            )}
            <strong>Öneri</strong><p>{finding.recommendation}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export function RiskCategories({ tags }: { tags: RiskTag[] }) {
  if (!tags.length) return <p className="analysis-empty">Risk kategorisi tespit edilmedi.</p>;
  return (
    <div className="risk-category-grid">
      {tags.map((tag) => <article key={tag}><span>{riskTagLabels[tag].slice(0, 1)}</span><strong>{riskTagLabels[tag]}</strong></article>)}
    </div>
  );
}
