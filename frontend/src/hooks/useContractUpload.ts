import { useCallback, useState } from "react";
import api from "../services/api";
import type { UploadResponse } from "../types";

export function useContractUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState("");

  const upload = useCallback(async (file: File) => {
    setError(""); setResult(null); setIsUploading(true);
    const formData = new FormData(); formData.append("file", file);
    try {
      const response = await api.post<UploadResponse>("/upload", formData, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(response.data);
    } catch { setError("Dosya yüklenirken bir hata oluştu."); }
    finally { setIsUploading(false); }
  }, []);

  return { upload, isUploading, result, error };
}
