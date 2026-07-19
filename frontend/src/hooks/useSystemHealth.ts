import { useCallback, useEffect, useState } from "react";
import api from "../services/api";

type SystemHealth = "checking" | "ready" | "limited" | "offline";

export function useSystemHealth(): SystemHealth {
  const [status, setStatus] = useState<SystemHealth>("checking");

  const check = useCallback(async () => {
    try {
      const [apiHealth, llmHealth] = await Promise.all([
        api.get<{ status: string }>("/health"),
        api.get<{ configured: boolean }>("/health/llm"),
      ]);
      setStatus(
        apiHealth.data.status === "ok" && llmHealth.data.configured
          ? "ready"
          : "limited",
      );
    } catch {
      setStatus("offline");
    }
  }, []);

  useEffect(() => {
    void check();
    const interval = window.setInterval(() => void check(), 60_000);
    return () => window.clearInterval(interval);
  }, [check]);

  return status;
}
