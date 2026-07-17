import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";
import { Icon } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import "./MainLayout.css";

export default function MainLayout() {
  const { user } = useAuth();
  return (
    <div className="main-layout">
      <Navbar />
      <div className="layout-workspace">
        <header className="top-navbar">
          <div><span className="topbar-product">Lexora</span><span className="topbar-divider" /><span>AI Sözleşme Platformu</span></div>
          <div className="topbar-actions"><span className="system-pill"><i /> Sistem hazır</span><button aria-label="Bildirimler"><Icon name="alert" /></button><div className="topbar-avatar">{user?.full_name?.slice(0,1).toUpperCase() ?? "K"}</div></div>
        </header>
        <main className="main-content"><Outlet /></main>
      </div>
    </div>
  );
}
