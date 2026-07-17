import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button, Icon } from "../components/ui";
import "./Login.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login({ username, password });
      navigate("/dashboard");
    } catch {
      setError("Geçersiz kullanıcı adı veya şifre");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-brand-panel">
        <div className="login-brand"><span>L</span><strong>Lexora</strong></div>
        <div className="login-value"><p>LEGAL INTELLIGENCE PLATFORM</p><h1>Hukuki çalışmaları<br />daha güvenilir hale getirin.</h1><span>Kaynaklandırılmış AI analizi, sözleşme karşılaştırma ve merkezi hukuk bilgi tabanı tek çalışma alanında.</span></div>
        <ul><li><Icon name="shield" />Trustworthy RAG ve doğrulanmış kaynaklar</li><li><Icon name="activity" />Açıklanabilir risk ve compliance analizi</li><li><Icon name="book" />Merkezi mevzuat ve emsal karar altyapısı</li></ul>
        <small>© 2026 Lexora Legal Technologies</small>
      </section>
      <div className="login-form-side"><div className="login-container">
        <div className="login-header">
          <p>Güvenli çalışma alanı</p><h1>Tekrar hoş geldiniz</h1><span className="login-subtitle">Hesabınıza erişmek için bilgilerinizi girin.</span>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="login-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="username">Kullanıcı Adı</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Şifre</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <Button type="submit" icon="arrow" className="login-button" disabled={isSubmitting}>
            {isSubmitting ? "Giriş yapılıyor..." : "Giriş Yap"}
          </Button>
        </form>

        <div className="login-footer">
          <p>Demo çalışma alanı: admin / admin123</p>
        </div>
      </div></div>
    </div>
  );
}
