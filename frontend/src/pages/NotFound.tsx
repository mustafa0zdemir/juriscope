import { Link } from "react-router-dom";
import "./NotFound.css";
import { Button, Icon } from "../components/ui";

export default function NotFound() {
  return (
    <div className="notfound-page">
      <div className="notfound-content">
        <div className="notfound-icon"><Icon name="alert" size={28} /></div>
        <h1 className="notfound-code">404</h1>
        <h2>Sayfa Bulunamadı</h2>
        <p>Aradığınız sayfa mevcut değil veya taşınmış olabilir.</p>
        <Link to="/dashboard"><Button icon="arrow">Genel Bakışa Dön</Button></Link>
      </div>
    </div>
  );
}
