import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useAuth } from "../hooks/useAuth";
import { useSystemHealth } from "../hooks/useSystemHealth";
import "./MainLayout.css";

export default function MainLayout() {
  const { user } = useAuth();
  const systemHealth = useSystemHealth();
  const healthLabel = {
    checking: "Sistem kontrol ediliyor",
    ready: "Sistem hazır",
    limited: "Sınırlı hizmet",
    offline: "Bağlantı kurulamadı",
  }[systemHealth];
  return (
    <div className="main-layout">
      <Navbar />
      <div className="layout-workspace">
        <header className="top-navbar">
          <div><span className="topbar-product">Sözleşme Analizi</span><span className="topbar-divider" /><span>Yapay Zekâ Destekli Hukuk Platformu</span></div>
          <div className="topbar-actions"><span className={`system-pill system-${systemHealth}`} aria-live="polite"><i /> {healthLabel}</span><div className="topbar-avatar">{user?.full_name?.slice(0,1).toUpperCase() ?? "K"}</div></div>
        </header>
        <main className="main-content"><Outlet /></main>
      </div>
    </div>
  );
}
