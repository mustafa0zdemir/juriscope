import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
import "./ui.css";

export function Button({ children, icon, variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { icon?: IconName; variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  return <button className={`ui-button ui-button-${variant} ${className}`} {...props}>{icon && <Icon name={icon} />}{children}</button>;
}

export function Card({ children, className = "", ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={`ui-card ${className}`} {...props}>{children}</section>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  return <span className={`ui-badge ui-badge-${tone}`}>{children}</span>;
}

export function SectionHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <header className="section-header"><div>{eyebrow && <span>{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</header>;
}

export function EmptyState({ icon = "folder", title, description, action }: { icon?: IconName; title: string; description: string; action?: ReactNode }) {
  return <div className="ui-empty"><span><Icon name={icon} size={22} /></span><h3>{title}</h3><p>{description}</p>{action}</div>;
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return <div className="ui-skeleton" aria-label="Yükleniyor">{Array.from({ length: lines }, (_, index) => <span key={index} />)}</div>;
}

export function StatCard({ icon, label, value, helper, tone = "neutral" }: { icon: IconName; label: string; value: string | number; helper?: string; tone?: "neutral" | "success" | "warning" | "danger" }) {
  return <Card className="ui-stat-card"><div className={`ui-stat-icon tone-${tone}`}><Icon name={icon} /></div><div><span>{label}</span><strong>{value}</strong>{helper && <small>{helper}</small>}</div></Card>;
}

export { Icon } from "./Icon";
