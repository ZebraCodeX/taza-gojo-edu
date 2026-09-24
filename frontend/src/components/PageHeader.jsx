
export default function PageHeader({ icon, title, subtitle, actions }) {
  return (
    <div className="page-head">
      {icon && <div className="ph-ico">{icon}</div>}
      <div style={{ minWidth: 0 }}>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}
