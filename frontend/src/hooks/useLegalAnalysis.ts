import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import type {
  ClauseListResponse,
  ComplianceReport,
  Contract,
  ExplainableAnalysis,
  LegalAnalysis,
} from "../types";

interface UseLegalAnalysisResult {
  contract: Contract | null;
  analysis: LegalAnalysis | null;
  explanation: ExplainableAnalysis | null;
  clauses: ClauseListResponse | null;
  compliance: ComplianceReport | null;
  isLoading: boolean;
  isAnalyzing: boolean;
  activeOperation: AnalysisOperation | null;
  error: string;
  analyze: () => Promise<boolean>;
  explain: () => Promise<boolean>;
  detectClauses: () => Promise<boolean>;
  checkCompliance: () => Promise<boolean>;
}

export type AnalysisOperation = "general" | "explanation" | "clauses" | "compliance";

interface InsufficientContextResponse {
  status: "insufficient_context";
  message?: string;
}

function isInsufficientContext(data: unknown): data is InsufficientContextResponse {
  return typeof data === "object"
    && data !== null
    && "status" in data
    && data.status === "insufficient_context";
}

export function useLegalAnalysis(contractId: number | null): UseLegalAnalysisResult {
  const [contract, setContract] = useState<Contract | null>(null);
  const [analysis, setAnalysis] = useState<LegalAnalysis | null>(null);
  const [explanation, setExplanation] = useState<ExplainableAnalysis | null>(null);
  const [clauses, setClauses] = useState<ClauseListResponse | null>(null);
  const [compliance, setCompliance] = useState<ComplianceReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeOperation, setActiveOperation] = useState<AnalysisOperation | null>(null);
  const [error, setError] = useState("");
  const isAnalyzing = activeOperation !== null;

  useEffect(() => {
    if (!contractId) {
      setError("Geçersiz sözleşme seçildi");
      setIsLoading(false);
      return;
    }

    const loadContract = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await api.get<Contract>(`/contracts/${contractId}`);
        setContract(response.data);
      } catch {
        setError("Sözleşme bilgileri yüklenemedi");
      } finally {
        setIsLoading(false);
      }
    };

    void loadContract();
  }, [contractId]);

  const analyze = useCallback(async () => {
    if (!contractId || activeOperation) return false;

    setActiveOperation("general");
    setError("");
    try {
      const response = await api.post<LegalAnalysis | InsufficientContextResponse>(`/contracts/${contractId}/analyze`, {
        analysis_type: "full",
      });
      if (isInsufficientContext(response.data)) {
        setError(response.data.message || "Güvenilir analiz için yeterli mevzuat/kaynak bulunamadı.");
        return false;
      }
      setAnalysis(response.data);
      return true;
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail ?? "Sözleşme analizi tamamlanamadı");
      return false;
    } finally {
      setActiveOperation(null);
    }
  }, [activeOperation, contractId]);

  const runRequest = useCallback(async <T,>(
    operation: AnalysisOperation,
    request: () => Promise<T>,
    apply: (data: T) => void,
  ) => {
    if (!contractId || activeOperation) return false;
    setActiveOperation(operation);
    setError("");
    try {
      const data = await request();
      if (isInsufficientContext(data)) {
        setError(data.message || "Güvenilir analiz için yeterli mevzuat/kaynak bulunamadı.");
        return false;
      }
      apply(data);
      return true;
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail ?? "Analiz işlemi tamamlanamadı");
      return false;
    } finally {
      setActiveOperation(null);
    }
  }, [activeOperation, contractId]);

  const explain = useCallback(async () => {
    return runRequest(
      "explanation",
      async () => (await api.post<ExplainableAnalysis>(`/contracts/${contractId}/analysis/explain`)).data,
      (data) => {
        setExplanation(data);
        setAnalysis(data.analysis);
      },
    );
  }, [contractId, runRequest]);

  const detectClauses = useCallback(async () => {
    return runRequest(
      "clauses",
      async () => (await api.get<ClauseListResponse>(`/contracts/${contractId}/clauses`)).data,
      setClauses,
    );
  }, [contractId, runRequest]);

  const checkCompliance = useCallback(async () => {
    return runRequest(
      "compliance",
      async () => (await api.post<ComplianceReport>(`/contracts/${contractId}/compliance`)).data,
      setCompliance,
    );
  }, [contractId, runRequest]);

  return {
    contract,
    analysis,
    explanation,
    clauses,
    compliance,
    isLoading,
    isAnalyzing,
    activeOperation,
    error,
    analyze,
    explain,
    detectClauses,
    checkCompliance,
  };
}
