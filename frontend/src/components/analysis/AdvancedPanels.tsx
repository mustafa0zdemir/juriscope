import type { ClauseListResponse, ComplianceReport, RiskTag } from "../../types";

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
              {clause.risk_tags.map((tag) => <span key={tag}>{tag}</span>)}
            </div>
            <small>Sayfa {clause.page_number ?? "—"} · Chunk {clause.chunk_index}</small>
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
        <div><span>{report.status}</span><p>{report.disclaimer}</p></div>
      </div>
      <div className="finding-list">
        {report.findings.map((finding) => (
          <article className="compliance-card" key={finding.law}>
            <div className="risk-card-header"><h3>{finding.law}</h3><span>{finding.status}</span></div>
            {finding.issues.length > 0
              ? <ul>{finding.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
              : <p>Temel madde kategorilerinin tamamı tespit edildi.</p>}
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
      {tags.map((tag) => <article key={tag}><span>{tag.slice(0, 1)}</span><strong>{tag}</strong></article>)}
    </div>
  );
}
