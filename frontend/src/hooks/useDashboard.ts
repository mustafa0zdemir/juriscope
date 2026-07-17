import { useEffect, useMemo, useState } from "react";
import api from "../services/api";
import type { Contract, ContractListResponse, Conversation } from "../types";

export function useDashboard() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [contractResponse, conversationResponse] = await Promise.all([
          api.get<ContractListResponse>("/contracts"),
          api.get<Conversation[]>("/conversations"),
        ]);
        setContracts(contractResponse.data.items);
        setConversations(conversationResponse.data);
      } catch {
        setError("Çalışma alanı verileri yüklenemedi.");
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, []);

  const metrics = useMemo(() => ({
    total: contracts.length,
    ready: contracts.filter((contract) => contract.status === "embedded").length,
    pending: contracts.filter((contract) => contract.status !== "embedded" && contract.status !== "failed").length,
    failed: contracts.filter((contract) => contract.status === "failed").length,
  }), [contracts]);

  return { contracts, conversations, metrics, isLoading, error };
}
