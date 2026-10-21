"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Beranda() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/health").then(setHealth).catch((e) => setError(e.message));
  }, []);

  const dbOk = health?.database === "terhubung";

  return (
    <>
      <h1>Human GVC</h1>
      <p className="lead">
        Analisis variant calling data sekuens manusia: dari unggah FASTQ sampai hasil varian
        yang dapat ditelusuri. Halaman ini memeriksa sambungan antarkomponen aplikasi.
      </p>
      <section className="panel">
        <h2>Status sistem</h2>
        <div className="status-row"><span className="dot ok" /> Frontend berjalan</div>
        <div className="status-row">
          <span className={`dot ${health ? "ok" : error ? "bad" : ""}`} />
          Backend API: {health ? "terhubung" : error ? "tidak terhubung" : "memeriksa..."}
        </div>
        <div className="status-row">
          <span className={`dot ${health ? (dbOk ? "ok" : "bad") : ""}`} />
          Database PostgreSQL: {health ? health.database : "memeriksa..."}
        </div>
        {error && <p className="msg-error">{error}</p>}
      </section>
    </>
  );
}
