import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import api from "../services/api";
import type { Contract, ContractListResponse } from "../types";
import "./Dashboard.css";

export default function Dashboard() {
  const { user } = useAuth();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadContracts = async () => {
      try {
        const response = await api.get<ContractListResponse>("/contracts");
        setContracts(response.data.items);
      } finally {
        setIsLoading(false);
      }
    };
    void loadContracts();
  }, []);

  const readyContracts = contracts.filter((contract) => contract.status === "embedded").length;
  const pendingContracts = contracts.filter((contract) => contract.status !== "embedded").length;

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p className="dashboard-welcome">
          Hoş geldiniz, <strong>{user?.full_name}</strong>
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-icon contracts">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{contracts.length}</span>
            <span className="stat-label">Toplam Sözleşme</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon analyzed">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{readyContracts}</span>
            <span className="stat-label">Analize Hazır</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon pending">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{pendingContracts}</span>
            <span className="stat-label">İşleniyor</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon risk">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{readyContracts}</span>
            <span className="stat-label">Analiz Edilebilir</span>
          </div>
        </div>
      </div>

      {user?.is_admin && (
        <Link className="legal-kb-banner" to="/legal-kb">
          <div>
            <span className="eyebrow">YÖNETİCİ</span>
            <strong>Legal Knowledge Base</strong>
            <p>Kanun, yönetmelik ve emsal kararları merkezi bilgi tabanında yönetin.</p>
          </div>
          <span>Yönetim ekranını aç →</span>
        </Link>
      )}

      <div className="dashboard-section">
        <h2>Sözleşmeler</h2>
        {!isLoading && contracts.length > 0 ? (
          <div className="contract-list">
            {contracts.map((contract) => (
              <Link className="contract-list-item" key={contract.id} to={`/contracts/${contract.id}`}>
                <div>
                  <strong>{contract.original_filename}</strong>
                  <span>{new Date(contract.uploaded_at).toLocaleDateString("tr-TR")}</span>
                </div>
                <span className={`dashboard-contract-status status-${contract.status}`}>{contract.status}</span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          <p>Henüz bir aktivite bulunmuyor</p>
          <span>Sözleşme yükleyerek başlayabilirsiniz</span>
          </div>
        )}
      </div>
    </div>
  );
}
