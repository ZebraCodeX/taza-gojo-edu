import React from "react";

export default function Empty({ icon = "🗂", title, text, action }) {
  return (
    <div className="empty">
      <span className="e-ico">{icon}</span>
      {title && <b>{title}</b>}
      {text && <p className="small" style={{ margin: "4px auto 12px", maxWidth: 420 }}>{text}</p>}
      {action}
    </div>
  );
}
