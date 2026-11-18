"use client";
import { STATUS_LABEL, STATUS_TONE } from "../lib/constants";

export const Card = ({ title, dot = "", right, children }) => (
  <section className="card">
    {title && <h2><span className={`dot ${dot}`} />{title}{right && <span className="r">{right}</span>}</h2>}
    {children}
  </section>
);
export const Badge = ({ tone = "", children }) => <span className={`badge ${tone}`}>{children}</span>;
export const StatusBadge = ({ status }) => <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status] || status}</Badge>;
export const Alert = ({ type = "info", children }) => children ? <div className={`alert ${type}`} role={type === "err" ? "alert" : "status"}>{children}</div> : null;
export const Field = ({ label, hint, error, children }) => (
  <label className="f">{label}{hint && <small>{hint}</small>}{children}{error && <span className="ferr">{error}</span>}</label>
);
export const Modal = ({ title, onClose, children }) => (
  <div className="modal" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
    <div role="dialog" aria-modal="true" aria-label={title}><h3>{title}</h3>{children}</div>
  </div>
);
export const Empty = ({ children }) => <div className="empty">{children}</div>;
export const CloudIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 10a6 6 0 0 0-11.5-2A4.5 4.5 0 0 0 7 17h2"/><path d="M12 12v9M8.5 15.5 12 12l3.5 3.5"/></svg>
);
export const FlaskIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3"/></svg>
);
