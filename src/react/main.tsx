import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type Stats = { accounts?: number; applications?: number; licenses?: number; activeUsers?: number };
type Me = { success?: boolean; username?: string };

function ReactCta() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    fetch("./stats.php")
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => setStats(null));
    fetch("/api/me")
      .then((r) => (r.ok ? r.json() : null))
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  const signedIn = !!(me && me.success && me.username);
  const chips: Array<[string, number | undefined]> = [
    ["Accounts", stats?.accounts],
    ["Apps", stats?.applications],
    ["Licenses", stats?.licenses],
  ];
  const hasStats = chips.some(([, v]) => typeof v === "number");

  return (
    <div
      id="react-cta"
      className="glass-card"
      style={{
        maxWidth: "1120px",
        margin: "0 auto 64px",
        padding: "32px 36px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "24px",
        flexWrap: "wrap",
      }}
    >
      <div style={{ minWidth: 260 }}>
        <h3 style={{ margin: "0 0 6px", fontSize: "1.35rem", fontWeight: 800 }}>
          <span className="shimmer-text">Ready to protect your software?</span>
        </h3>
        <p style={{ margin: 0, opacity: 0.75 }}>
          {signedIn
            ? `Welcome back, ${me!.username}. Your applications are waiting.`
            : "Create your free account and start authenticating in minutes."}
        </p>
        {hasStats && (
          <div style={{ display: "flex", gap: "10px", marginTop: "14px", flexWrap: "wrap" }}>
            {chips.map(([label, value]) =>
              typeof value === "number" ? (
                <span
                  key={label}
                  style={{
                    fontSize: ".8rem",
                    padding: "4px 12px",
                    borderRadius: "999px",
                    border: "1px solid rgba(59,130,246,.35)",
                    background: "rgba(59,130,246,.08)",
                  }}
                >
                  {value.toLocaleString()} {label}
                </span>
              ) : null
            )}
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <a
          href={signedIn ? "./app/" : "./register/"}
          className="btn btn-glow"
          style={{ padding: "12px 26px", fontWeight: 700, whiteSpace: "nowrap" }}
        >
          {signedIn ? "Open Dashboard" : "Get Started Free"}{" "}
          <i className="fa fa-arrow-right" style={{ marginLeft: 6 }} />
        </a>
        <a
          href={signedIn ? "./register/" : "./login/"}
          className="btn"
          style={{
            padding: "12px 26px",
            fontWeight: 700,
            whiteSpace: "nowrap",
            border: "1px solid rgba(148,163,184,.35)",
          }}
        >
          {signedIn ? "New App" : "Sign In"}
        </a>
      </div>
    </div>
  );
}

let host = document.getElementById("react-cta-root");
if (!host) {
  host = document.createElement("div");
  host.id = "react-cta-root";
  document.body.appendChild(host);
}
createRoot(host).render(<ReactCta />);
