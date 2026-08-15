import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button, Icon } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import "./Login.css";

function errorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) return "Hesap oluşturulamadı";
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
    return detail[0].msg.replace("Value error, ", "");
  }
  return "Hesap oluşturulamadı";
}

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    password_confirmation: "",
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (isSubmitting) return;
    setError("");

    if (form.password !== form.password_confirmation) {
      setError("Şifreler eşleşmiyor.");
      return;
    }

    const hasUpperCase = /[A-Z]/.test(form.password);
    const hasLowerCase = /[a-z]/.test(form.password);
    const hasNumbers = /\d/.test(form.password);
    const hasNonalphas = /\W/.test(form.password);

    if (form.password.length < 12 || !hasUpperCase || !hasLowerCase || !hasNumbers || !hasNonalphas) {
      setError("Şifre güçlü parola kurallarına uymuyor. En az 12 karakter; en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(form);
      navigate("/dashboard");
    } catch (registerError) {
      setError(errorMessage(registerError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-brand-panel">
        <div className="login-brand"><span>J</span><strong>Juriscope</strong></div>
        <div className="login-value"><p>YAPAY ZEKÂ DESTEKLİ SÖZLEŞME İNCELEME PLATFORMU</p><h1>Hukuki verilerinizi<br />güvenle yönetin.</h1><span>Her kullanıcı yalnızca kendi sözleşmelerine ve sohbet kayıtlarına erişebilir.</span></div>
        <ul><li><Icon name="shield" />Güçlü parola ve hesap kilitleme</li><li><Icon name="user" />Kullanıcı bazlı veri izolasyonu</li><li><Icon name="activity" />Denetlenebilir güvenlik olayları</li></ul>
        <small>© 2026 Juriscope</small>
      </section>
      <div className="login-form-side"><div className="login-container">
        <div className="login-header"><p>Yeni çalışma alanı</p><h1>Hesap oluşturun</h1><span className="login-subtitle">Bilgileriniz güvenli oturum altyapısıyla korunur.</span></div>
        <form onSubmit={submit} className="login-form">
          {error && <div className="login-error">{error}</div>}
          <div className="form-group"><label htmlFor="full-name">Ad Soyad</label><input id="full-name" value={form.full_name} onChange={(event) => update("full_name", event.target.value)} required autoComplete="name" /></div>
          <div className="form-group"><label htmlFor="register-username">Kullanıcı Adı</label><input id="register-username" value={form.username} onChange={(event) => update("username", event.target.value)} required autoComplete="username" /></div>
          <div className="form-group"><label htmlFor="email">E-posta</label><input id="email" type="email" value={form.email} onChange={(event) => update("email", event.target.value)} required autoComplete="email" /></div>
          <div className="form-group"><label htmlFor="register-password">Şifre</label><input id="register-password" type="password" value={form.password} onChange={(event) => update("password", event.target.value)} required autoComplete="new-password" /></div>
          <div className="form-group"><label htmlFor="password-confirmation">Şifre Tekrarı</label><input id="password-confirmation" type="password" value={form.password_confirmation} onChange={(event) => update("password_confirmation", event.target.value)} required autoComplete="new-password" /></div>
          <p className="password-guidance">En az 12 karakter; büyük harf, küçük harf, rakam ve özel karakter kullanın.</p>
          <Button type="submit" icon="arrow" disabled={isSubmitting}>{isSubmitting ? "Hesap oluşturuluyor..." : "Güvenli Hesap Oluştur"}</Button>
        </form>
        <div className="login-footer"><p>Zaten hesabınız var mı? <Link to="/login">Giriş yapın</Link></p></div>
      </div></div>
    </div>
  );
}
