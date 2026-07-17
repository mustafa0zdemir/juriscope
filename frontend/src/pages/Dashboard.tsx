import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useDashboard } from "../hooks/useDashboard";
import { Badge, Button, Card, EmptyState, Icon, SectionHeader, Skeleton, StatCard } from "../components/ui";
import "./Dashboard.css";

function statusTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "embedded") return "success";
  if (status === "failed") return "danger";
  if (["uploaded", "parsing", "chunking", "embedding"].includes(status)) return "warning";
  return "neutral";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

export default function Dashboard() {
  const { user } = useAuth();
  const dashboard = useDashboard();
  const recentContracts = dashboard.contracts.slice(0, 5);
  const recentConversations = dashboard.conversations.slice(0, 4);

  return (
    <div className="dashboard-page">
      <SectionHeader
        eyebrow="Çalışma Alanı"
        title={`Günaydın, ${user?.full_name?.split(" ")[0] ?? "Kullanıcı"}`}
        description="Sözleşmelerinizi, hukuki analizlerinizi ve AI çalışmalarınızı tek merkezden yönetin."
        action={<Link to="/upload"><Button icon="plus">Yeni sözleşme</Button></Link>}
      />
      {dashboard.error && <div className="dashboard-alert"><Icon name="alert" />{dashboard.error}</div>}

      <div className="dashboard-grid">
        <StatCard icon="document" label="Toplam Sözleşme" value={dashboard.metrics.total} helper="Tüm çalışma alanı" />
        <StatCard icon="check" label="İşlenen Sözleşmeler" value={dashboard.metrics.ready} helper="Analize hazır" tone="success" />
        <StatCard icon="clock" label="Bekleyen Analizler" value={dashboard.metrics.pending} helper="Pipeline devam ediyor" tone="warning" />
        <StatCard icon="alert" label="Riskli Sözleşmeler" value={dashboard.metrics.failed || "—"} helper="İnceleme gerektiren" tone="danger" />
        <StatCard icon="shield" label="Compliance Ortalaması" value="—" helper="Raporlar sonrası hesaplanır" />
      </div>

      <div className="dashboard-layout">
        <Card className="dashboard-primary-panel">
          <div className="panel-heading"><div><span>SON ANALİZLER</span><h2>Sözleşmeler</h2></div><Link to="/upload">Tümünü yönet <Icon name="arrow" size={15} /></Link></div>
          {dashboard.isLoading ? <Skeleton lines={5} /> : recentContracts.length ? (
            <div className="contract-table" role="table" aria-label="Son sözleşmeler">
              <div className="contract-table-head" role="row"><span>Dosya</span><span>Durum</span><span>Tarih</span><span /></div>
              {recentContracts.map((contract) => (
                <Link className="contract-table-row" key={contract.id} to={`/contracts/${contract.id}`} role="row">
                  <span className="contract-name"><i><Icon name="document" size={17} /></i><span><strong>{contract.original_filename}</strong><small>{(contract.file_size / 1024).toFixed(1)} KB</small></span></span>
                  <span><Badge tone={statusTone(contract.status)}>{contract.status}</Badge></span>
                  <time>{formatDate(contract.updated_at)}</time><Icon name="chevron" size={16} />
                </Link>
              ))}
            </div>
          ) : <EmptyState title="Henüz sözleşme yok" description="İlk sözleşmenizi yükleyerek analiz çalışma alanını oluşturun." action={<Link to="/upload"><Button icon="upload">Sözleşme yükle</Button></Link>} />}
        </Card>

        <div className="dashboard-side-column">
          <Card className="quick-actions"><div className="panel-heading"><div><span>HIZLI İŞLEMLER</span><h2>Başlayın</h2></div></div><div className="quick-action-grid">
            <Link to="/upload"><Icon name="upload" /><span><strong>Sözleşme yükle</strong><small>PDF veya DOCX</small></span></Link>
            <Link to="/chat"><Icon name="sparkle" /><span><strong>AI'a danış</strong><small>Kaynaklı cevap</small></span></Link>
            <Link to="/compare"><Icon name="compare" /><span><strong>Karşılaştır</strong><small>İki sürümü incele</small></span></Link>
            {user?.is_admin && <Link to="/legal-kb"><Icon name="book" /><span><strong>Legal KB</strong><small>Kaynakları yönet</small></span></Link>}
          </div></Card>
          <Card className="recent-chats"><div className="panel-heading"><div><span>SON SOHBETLER</span><h2>AI Oturumları</h2></div><Link to="/chat">Aç</Link></div>
            {recentConversations.length ? recentConversations.map((conversation) => <Link to="/chat" key={conversation.id}><i><Icon name="chat" size={16} /></i><span><strong>{conversation.title}</strong><small>{formatDate(conversation.updated_at)}</small></span></Link>) : <EmptyState icon="chat" title="Sohbet bulunmuyor" description="AI asistanıyla yeni bir oturum başlatın." />}
          </Card>
        </div>
      </div>

      <Card className="recent-activity"><div className="panel-heading"><div><span>RECENT ACTIVITY</span><h2>Son hareketler</h2></div></div><div className="activity-list">{recentContracts.slice(0, 3).map((contract) => <div key={contract.id}><i><Icon name="activity" size={15} /></i><p><strong>{contract.original_filename}</strong> için işlem durumu <Badge tone={statusTone(contract.status)}>{contract.status}</Badge> olarak güncellendi.</p><time>{formatDate(contract.updated_at)}</time></div>)}</div></Card>
    </div>
  );
}
