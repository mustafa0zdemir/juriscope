import { useCallback, useEffect, useState, type FormEvent } from "react";
import axios from "axios";
import api from "../services/api";
import type { UserSession } from "../types";
import { Badge, Button, EmptyState, SectionHeader } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import "./SecuritySettings.css";

function messageFrom(error: unknown): string {
  if (!axios.isAxiosError(error)) return "İşlem tamamlanamadı";
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg.replace("Value error, ", "");
  return "İşlem tamamlanamadı";
}

export default function SecuritySettings() {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({ current_password: "", new_password: "", new_password_confirmation: "" });

  const loadSessions = useCallback(async () => {
    try {
      const response = await api.get<UserSession[]>("/auth/sessions");
      setSessions(response.data);
    } catch (loadError) {
      setError(messageFrom(loadError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void loadSessions(); }, [loadSessions]);

  const changePassword = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api.post("/auth/change-password", form);
      setNotice("Şifreniz değiştirildi. Güvenliğiniz için yeniden giriş yapın.");
      setTimeout(() => { void logout(); }, 1200);
    } catch (changeError) {
      setError(messageFrom(changeError));
    }
  };

  const revoke = async (sessionId: string) => {
    try {
      await api.delete(`/auth/sessions/${sessionId}`);
      setSessions((current) => current.filter((session) => session.id !== sessionId));
    } catch (revokeError) {
      setError(messageFrom(revokeError));
    }
  };

  return (
    <section className="security-page">
      <SectionHeader eyebrow="Hesap Yönetimi" title="Hesap Güvenliği" description="Parolanızı ve etkin oturumlarınızı güvenli biçimde yönetin." />
      {error && <div className="security-message error">{error}</div>}
      {notice && <div className="security-message success">{notice}</div>}
      <div className="security-grid">
        <form className="security-card" onSubmit={changePassword}>
          <div><h2>Şifre Değiştir</h2><p>Şifre değişikliğinde tüm etkin oturumlar kapatılır.</p></div>
          <label>Mevcut Şifre<input type="password" value={form.current_password} onChange={(event) => setForm({ ...form, current_password: event.target.value })} required autoComplete="current-password" /></label>
          <label>Yeni Şifre<input type="password" value={form.new_password} onChange={(event) => setForm({ ...form, new_password: event.target.value })} required autoComplete="new-password" /></label>
          <label>Yeni Şifre Tekrarı<input type="password" value={form.new_password_confirmation} onChange={(event) => setForm({ ...form, new_password_confirmation: event.target.value })} required autoComplete="new-password" /></label>
          <small>En az 12 karakter; büyük/küçük harf, rakam ve özel karakter zorunludur.</small>
          <Button type="submit" icon="shield">Şifreyi Güvenle Değiştir</Button>
        </form>
        <div className="security-card profile-security">
          <div><h2>Hesap Durumu</h2><p>Kimlik ve yetki bilgileriniz.</p></div>
          <dl><div><dt>Ad Soyad</dt><dd>{user?.full_name || "Belirtilmedi"}</dd></div><div><dt>E-posta</dt><dd>{user?.email}</dd></div><div><dt>Yetki</dt><dd><Badge tone={user?.is_admin ? "warning" : "info"}>{user?.is_admin ? "Yönetici" : "Kullanıcı"}</Badge></dd></div><div><dt>Hesap</dt><dd><Badge tone="success">Etkin</Badge></dd></div></dl>
        </div>
      </div>
      <div className="security-card sessions-card">
        <div><h2>Etkin Oturumlar</h2><p>Hesabınıza erişebilen cihazları inceleyin ve gerektiğinde sonlandırın.</p></div>
        {isLoading ? <div className="security-loading"><span className="spinner" /></div> : sessions.length === 0 ? <EmptyState icon="shield" title="Etkin oturum bulunamadı" description="Yeni girişler burada görüntülenecektir." /> : <div className="session-list">{sessions.map((session) => <article key={session.id}><div><strong>{session.user_agent || "Bilinmeyen cihaz"}</strong><span>{session.ip_address || "IP bilgisi yok"} · {new Date(session.last_used_at).toLocaleString("tr-TR")}</span></div><Button variant="secondary" icon="logout" onClick={() => void revoke(session.id)}>Oturumu Sonlandır</Button></article>)}</div>}
      </div>
    </section>
  );
}
