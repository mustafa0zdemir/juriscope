import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import type { Contract, LegalAnalysis } from "../types";

interface UseLegalAnalysisResult {
  contract: Contract | null;
  analysis: LegalAnalysis | null;
  isLoading: boolean;
  isAnalyzing: boolean;
  error: string;
  analyze: () => Promise<void>;
}

export function useLegalAnalysis(contractId: number | null): UseLegalAnalysisResult {
  const [contract, setContract] = useState<Contract | null>(null);
  const [analysis, setAnalysis] = useState<LegalAnalysis | null>(null);
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

  return { contract, analysis, isLoading, isAnalyzing, error, analyze };
}
