"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";

// Kolom yang tidak diisi manual: kunci utama dan metadata otomatis.
// id_pengguna tetap ditampilkan sementara (login belum ada).
const SKIP = (c, pk) =>
  c === pk || c.startsWith("dibuat") || (c.startsWith("id_") && c !== "id_pengguna");

const TIPE_BACA = ["single-end", "paired-end"];

export default function Sampel() {
  const [rows, setRows] = useState([]);
  const [cols, setCols] = useState([]);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState({ type: "", text: "" });

  const load = () =>
    api("/api/sampel").then(setRows).catch((e) => setMsg({ type: "error", text: e.message }));

  useEffect(() => {
    api("/api/sampel/kolom").then(setCols).catch(() => {});
    load();
  }, []);

  const paired = form.tipe_baca === "paired-end";
  // lokasi_fastq_r2 hanya relevan untuk paired-end (BR-03)
  const fields = cols.filter((c) => !SKIP(c, cols[0]) && (c !== "lokasi_fastq_r2" || paired));
  const headers = rows[0] ? Object.keys(rows[0]) : cols;

  const set = (f, v) => setForm({ ...form, [f]: v });

  async function submit(e) {
    e.preventDefault();
    setMsg({ type: "", text: "" });
    if (!form.tipe_baca) return setMsg({ type: "error", text: "Pilih tipe baca terlebih dahulu." });
    try {
      await api("/api/sampel", { method: "POST", body: JSON.stringify(form) });
      setForm({});
      setMsg({ type: "ok", text: "Sampel tersimpan." });
      load();
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    }
  }

  return (
    <>
      <h1>Sampel</h1>
      <p className="lead">Metadata sampel (UC-01). Unggah berkas FASTQ ditambahkan pada tahap berikutnya.</p>

      <section className="panel">
        <h2>Tambah sampel</h2>
        <form onSubmit={submit}>
          {fields.map((f) =>
            f === "tipe_baca" ? (
              <label key={f}>
                tipe baca
                <select value={form[f] || ""} onChange={(e) => set(f, e.target.value)}>
                  <option value="">Pilih...</option>
                  {TIPE_BACA.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </label>
            ) : (
              <label key={f}>
                {f.replaceAll("_", " ")}
                <input
                  value={form[f] || ""}
                  onChange={(e) => set(f, e.target.value)}
                  type={f === "id_pengguna" ? "number" : "text"}
                />
              </label>
            )
          )}
          <button disabled={!fields.length}>Simpan</button>
          {msg.text && <span className={msg.type === "ok" ? "msg-ok" : "msg-error"}>{msg.text}</span>}
        </form>
      </section>

      <section className="panel">
        <h2>Daftar sampel</h2>
        {rows.length === 0 ? (
          <p className="muted">Belum ada sampel.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>{headers.map((h) => <td key={h}>{String(r[h] ?? "")}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
