import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import type { Contract, ContractComparison, ContractListResponse } from "../types";

export function useContractComparison() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [baseId, setBaseId] = useState<number | null>(null);
  const [comparisonId, setComparisonId] = useState<number | null>(null);
  const [result, setResult] = useState<ContractComparison | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await api.get<ContractListResponse>("/contracts");
        const ready = response.data.items.filter((contract) => contract.status === "embedded");
        setContracts(ready);
        setBaseId(ready[0]?.id ?? null);
        setComparisonId(ready[1]?.id ?? null);
      } catch {
        setError("Sözleşmeler yüklenemedi");
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, []);

  const compare = useCallback(async () => {
    if (!baseId || !comparisonId || baseId === comparisonId || isComparing) return;
    setIsComparing(true);
    setError("");
    try {
      const response = await api.post<ContractComparison>("/contracts/compare", {
        base_contract_id: baseId,
        comparison_contract_id: comparisonId,
      });
      setResult(response.data);
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail ?? "Sözleşmeler karşılaştırılamadı");
    } finally {
      setIsComparing(false);
    }
  }, [baseId, comparisonId, isComparing]);

  return {
    contracts,
    baseId,
    comparisonId,
    result,
    isLoading,
    isComparing,
    error,
    setBaseId,
    setComparisonId,
    compare,
  };
}
