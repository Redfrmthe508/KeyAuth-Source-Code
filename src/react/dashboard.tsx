import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type Me = { success?: boolean; username?: string };

function DashboardPanel() {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    fetch("/api/me")
      .then((r) => (r.ok ? r.json() : null))
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  const username = me && me.success ? me.username : null;

  return (
    <div
      id="react-dash"
      className="glass-card"
      style={{ padding: "24px 28px", marginBottom: "24px" }}
    >
      <h4 style={{ margin: "0 0 4px", fontSize: "1.2rem", fontWeight: 800 }}>
        <span className="shimmer-text">
          {username ? `Welcome back, ${username} 👋` : "Dashboard"}
        </span>
      </h4>
      <p style={{ margin: 0, opacity: 0.75 }}>
        {username
          ? "Session active — manage your applications, licenses, and users below."
          : "Loading your session…"}
      </p>
    </div>
  );
}

const host = document.getElementById("react-dash-root");
if (host) {
  createRoot(host).render(<DashboardPanel />);
}
