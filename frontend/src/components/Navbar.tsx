import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import "./Navbar.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span>Sözleşme Analizi</span>
      </div>

      <div className="navbar-links">
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Dashboard
        </NavLink>
        <NavLink to="/upload" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Yükle
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Sohbet
        </NavLink>
      </div>

      <div className="navbar-user">
        <span className="user-name">{user?.full_name}</span>
        <button onClick={handleLogout} className="logout-button">
          Çıkış
        </button>
      </div>
    </nav>
  );
}
