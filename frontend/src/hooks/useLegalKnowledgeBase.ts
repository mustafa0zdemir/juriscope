import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import type { LegalDocument, LegalDocumentListResponse } from "../types";

export interface LegalUploadValues {
  file: File;
  title: string;
  documentType: string;
  source: string;
  officialNumber: string;
  publicationDate: string;
}

export function useLegalKnowledgeBase(enabled: boolean) {
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<LegalDocument | null>(null);
  const [isLoading, setIsLoading] = useState(enabled);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  const loadDocuments = useCallback(async () => {
    if (!enabled) return;
    setIsLoading(true);
    setError("");
    try {
      const response = await api.get<LegalDocumentListResponse>("/legal");
      setDocuments(response.data.items);
      setSelectedDocument((current) => current ?? response.data.items[0] ?? null);
    } catch {
      setError("Hukuk bilgi tabanı yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const uploadDocument = useCallback(async (values: LegalUploadValues) => {
    setIsUploading(true);
    setError("");
    const formData = new FormData();
    formData.append("file", values.file);
    formData.append("title", values.title);
    formData.append("document_type", values.documentType);
    formData.append("source", values.source);
    if (values.officialNumber) formData.append("official_number", values.officialNumber);
    if (values.publicationDate) formData.append("publication_date", values.publicationDate);
    try {
      const response = await api.post<LegalDocument>("/legal/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDocuments((current) => [response.data, ...current]);
      setSelectedDocument(response.data);
    } catch {
      setError("Legal belge yüklenemedi");
      throw new Error("Legal belge yüklenemedi");
    } finally {
      setIsUploading(false);
    }
  }, []);

  const deleteDocument = useCallback(async (documentId: number) => {
    setError("");
    try {
      await api.delete(`/legal/${documentId}`);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      setSelectedDocument((current) => (current?.id === documentId ? null : current));
    } catch {
      setError("Legal belge silinemedi");
    }
  }, []);

  return {
    documents,
    selectedDocument,
    setSelectedDocument,
    isLoading,
    isUploading,
    error,
    uploadDocument,
    deleteDocument,
  };
}
