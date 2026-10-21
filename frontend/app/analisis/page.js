"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function Analisis() {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [log, setLog] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/analisis").then(setRows).catch((e) => setError(e.message));
  }, []);

  // Polling log proses tiap 3 detik (sesuai desain: antarmuka memantau log dengan polling)
  useEffect(() => {
    if (selected == null) return;
    const tick = () => api(`/api/analisis/${selected}/log`).then(setLog).catch(() => {});
    tick();
    const t = setInterval(tick, 3000);
    return () => clearInterval(t);
  }, [selected]);

  const headers = rows[0] ? Object.keys(rows[0]) : [];
  const pk = headers[0];

  return (
    <>
      <h1>Analisis</h1>
      <p className="lead">Daftar analisis dan log prosesnya (UC-04). Menjalankan analisis baru ditambahkan pada tahap pipeline.</p>
      {error && <p className="msg-error">{error}</p>}

      <section className="panel">
        <h2>Daftar analisis</h2>
        {rows.length === 0 ? (
          <p className="muted">Belum ada analisis.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className={`pick ${selected === r[pk] ? "selected" : ""}`} onClick={() => setSelected(r[pk])}>
                    {headers.map((h) => <td key={h}>{String(r[h] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected != null && (
        <section className="panel">
          <h2>Log proses analisis {selected}</h2>
          <div className="log">
            {log.length === 0 && <span className="muted">Belum ada catatan.</span>}
            {log.map((l, i) => (
              <div key={i} className={l.jenis_pesan}>
                {l.waktu} [{l.tahap || "-"}] {l.pesan}
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
