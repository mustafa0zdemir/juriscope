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
  error: string;
  analyze: () => Promise<void>;
  explain: () => Promise<boolean>;
  detectClauses: () => Promise<boolean>;
  checkCompliance: () => Promise<boolean>;
}

export function useLegalAnalysis(contractId: number | null): UseLegalAnalysisResult {
  const [contract, setContract] = useState<Contract | null>(null);
  const [analysis, setAnalysis] = useState<LegalAnalysis | null>(null);
  const [explanation, setExplanation] = useState<ExplainableAnalysis | null>(null);
  const [clauses, setClauses] = useState<ClauseListResponse | null>(null);
  const [compliance, setCompliance] = useState<ComplianceReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

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
    if (!contractId || isAnalyzing) return;

    setIsAnalyzing(true);
    setError("");
    try {
      const response = await api.post<LegalAnalysis>(`/contracts/${contractId}/analyze`, {
        analysis_type: "full",
      });
      setAnalysis(response.data);
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail ?? "Sözleşme analizi tamamlanamadı");
    } finally {
      setIsAnalyzing(false);
    }
  }, [contractId, isAnalyzing]);

  const runRequest = useCallback(async <T,>(request: () => Promise<T>, apply: (data: T) => void) => {
    if (!contractId || isAnalyzing) return false;
    setIsAnalyzing(true);
    setError("");
    try {
      apply(await request());
      return true;
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail ?? "Analiz işlemi tamamlanamadı");
      return false;
    } finally {
      setIsAnalyzing(false);
    }
  }, [contractId, isAnalyzing]);

  const explain = useCallback(async () => {
    return runRequest(
      async () => (await api.post<ExplainableAnalysis>(`/contracts/${contractId}/analysis/explain`)).data,
      (data) => {
        setExplanation(data);
        setAnalysis(data.analysis);
      },
    );
  }, [contractId, runRequest]);

  const detectClauses = useCallback(async () => {
    return runRequest(
      async () => (await api.get<ClauseListResponse>(`/contracts/${contractId}/clauses`)).data,
      setClauses,
    );
  }, [contractId, runRequest]);

  const checkCompliance = useCallback(async () => {
    return runRequest(
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
    error,
    analyze,
    explain,
    detectClauses,
    checkCompliance,
  };
}
