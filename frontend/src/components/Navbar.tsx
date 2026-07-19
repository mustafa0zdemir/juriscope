import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Icon, type IconName } from "./ui/Icon";
import "./Navbar.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="navbar" aria-label="Ana navigasyon">
      <div className="navbar-brand">
        <span className="brand-mark">S</span><span className="brand-copy"><strong>Sözleşme Analizi</strong><small>Yapay Zekâ Destekli Hukuk Platformu</small></span>
      </div>

      <div className="navbar-links">
        <span className="nav-section-label">Çalışma Alanı</span>
        {([['/dashboard','activity','Genel Bakış'],['/upload','upload','Sözleşme Yükle'],['/chat','chat','Hukuk Asistanı'],['/compare','compare','Karşılaştırma']] as Array<[string,IconName,string]>).map(([to,icon,label]) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><Icon name={icon} /><span>{label}</span></NavLink>)}
        {user?.is_admin && (
          <NavLink to="/legal-kb" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Icon name="book" /><span>Hukuk Bilgi Tabanı</span>
          </NavLink>
        )}
      </div>

      <div className="navbar-user">
        <div className="user-avatar">{user?.full_name?.slice(0,1).toUpperCase() ?? "K"}</div><span className="user-name"><strong>{user?.full_name}</strong><small>{user?.is_admin ? "Yönetici" : "Hukuk Kullanıcısı"}</small></span>
        <button type="button" onClick={handleLogout} className="logout-button">
          <Icon name="logout" /><span>Çıkış</span>
        </button>
      </div>
    </aside>
  );
}
