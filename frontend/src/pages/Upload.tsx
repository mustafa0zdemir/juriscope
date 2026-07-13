import { useState, useRef, type DragEvent, type ChangeEvent } from "react";
import api from "../services/api";
import type { UploadResponse } from "../types";
import "./Upload.css";

export default function Upload() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadFile = async (file: File) => {
    setError("");
    setResult(null);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.post<UploadResponse>("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);
    } catch {
      setError("Dosya yüklenirken bir hata oluştu");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1>Dosya Yükle</h1>
        <p>Analiz etmek istediğiniz sözleşmeyi yükleyin</p>
      </div>

      <div
        className={`upload-dropzone ${isDragging ? "dragging" : ""} ${isUploading ? "uploading" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          hidden
          accept=".pdf,.doc,.docx,.txt"
        />

        {isUploading ? (
          <div className="upload-loading">
            <div className="spinner" />
            <p>Yükleniyor...</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-text">
              Dosyayı sürükleyip bırakın veya <span>tıklayarak seçin</span>
            </p>
            <p className="upload-hint">PDF, DOC, DOCX, TXT — Maks. 50MB</p>
          </>
        )}
      </div>

      {error && <div className="upload-error">{error}</div>}

      {result && (
        <div className="upload-result">
          <div className="result-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div className="result-info">
            <h3>{result.message}</h3>
            <p>
              <strong>Dosya:</strong> {result.filename}
            </p>
            <p>
              <strong>Boyut:</strong> {formatFileSize(result.size)}
            </p>
            <p>
              <strong>Tür:</strong> {result.content_type}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
