import type { AttributedSource, ExplainableAnalysis } from "../../types";

function SourceCard({ source }: { source: AttributedSource }) {
  return (
    <div className="evidence-source">
      <strong>{source.title}</strong>
      <span>{source.article ? `Madde ${source.article}` : source.source_type}</span>
      <span>Sayfa {source.page ?? "—"} · Chunk {source.chunk}</span>
      <span>Benzerlik %{Math.round(source.similarity * 100)}</span>
      <span>Rerank {source.rerank_score?.toFixed(3) ?? "—"}</span>
      <p>{source.text_excerpt}</p>
    </div>
  );
}

export function ConfidencePanel({ explanation }: { explanation: ExplainableAnalysis }) {
  return (
    <div className="confidence-panel">
      <div className="confidence-heading">
        <strong>{explanation.confidence_score}/100</strong>
        <span>{explanation.confidence_level.replaceAll("_", " ")}</span>
      </div>
      <div className="confidence-track" aria-label={`Güven puanı ${explanation.confidence_score}`}>
        <div className="confidence-fill" style={{ width: `${explanation.confidence_score}%` }} />
      </div>
      <p>Model güveni, retrieval kalitesi, rerank skoru ve kaynak çeşitliliği birlikte değerlendirilmiştir.</p>
    </div>
  );
}

export function ReasoningPanel({ explanation }: { explanation: ExplainableAnalysis }) {
  if (!explanation.reasoning.length) return <p className="analysis-empty">Açıklanacak risk bulunamadı.</p>;
  return (
    <div className="finding-list">
      {explanation.reasoning.map((item) => (
        <article className="reasoning-card" key={item.risk_title}>
          <h3>{item.risk_title}</h3>
          <strong>Neden riskli?</strong><p>{item.why_risky}</p>
          <strong>Hukuki dayanak</strong><p>{item.law_basis}</p>
          <strong>Emsal karar desteği</strong><p>{item.case_support}</p>
          <strong>Etkilenen sözleşme maddesi</strong><p>{item.affected_clause}</p>
        </article>
      ))}
    </div>
  );
}

export function EvidencePanel({ explanation }: { explanation: ExplainableAnalysis }) {
  if (!explanation.evidence.length) return <p className="analysis-empty">Kanıt kaydı bulunamadı.</p>;
  return (
    <div className="evidence-list">
      {explanation.evidence.map((item) => (
        <article className="evidence-card" key={item.risk_title}>
          <h3>{item.risk_title}</h3>
          <div className="evidence-grid">
            {item.contract_chunk && <SourceCard source={item.contract_chunk} />}
            {item.law_chunk && <SourceCard source={item.law_chunk} />}
            {item.case_law_chunk && <SourceCard source={item.case_law_chunk} />}
          </div>
        </article>
      ))}
    </div>
  );
}

export function RetrievalPathPanel({ explanation }: { explanation: ExplainableAnalysis }) {
  return (
    <ol className="retrieval-timeline">
      {explanation.retrieval_path.map((step) => (
        <li key={step.stage}>
          <span className="timeline-dot" />
          <div>
            <strong>{step.stage}</strong>
            <p>{step.detail}</p>
            {step.hit_count !== null && <small>{step.hit_count} kaynak</small>}
          </div>
        </li>
      ))}
    </ol>
  );
}
