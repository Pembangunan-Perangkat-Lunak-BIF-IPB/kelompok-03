"use client";
import { useEffect, useState } from "react";
import { svc, saveBlob } from "../../../lib/api";
import { Alert, Badge, Card, Empty } from "../../../components/ui";

const SIZE = 20;
const AKSI = { login: "Masuk", lihat: "Melihat", unggah: "Mengunggah", ubah: "Mengubah", hapus: "Menghapus", jalankan: "Menjalankan", unduh: "Mengunduh", cari: "Mencari" };
const TONE = { login: "indigo", unggah: "green", jalankan: "green", hapus: "red", unduh: "amber", ubah: "amber" };
const KOSONG = { q: "", aksi: "", dari: "", sampai: "" };
const waktu = (s) => new Date(s).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "medium" });

export default function LogAktivitas() {
  const [f, setF] = useState(KOSONG); const [aktif, setAktif] = useState(KOSONG);
  const [page, setPage] = useState(1); const [data, setData] = useState({ total: 0, items: [] }); const [err, setErr] = useState("");

  useEffect(() => {
    svc.listLog({ ...aktif, page, size: SIZE }).then((d) => { setData(d); setErr(""); }).catch((e) => setErr(e.message));
  }, [aktif, page]);

  const terapkan = () => { setPage(1); setAktif(f); };
  const reset = () => { setF(KOSONG); setPage(1); setAktif(KOSONG); };
  const unduh = async () => { try { saveBlob(await svc.unduhLog(aktif)); } catch (e) { setErr(e.message); } };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const maks = Math.max(1, Math.ceil(data.total / SIZE));

  return (
    <>
      <Card title="Log Aktivitas Pengguna" dot="ind" right={<button className="btn sm" onClick={unduh}>Unduh CSV</button>}>
        <Alert type="err">{err}</Alert>
        <div className="filters">
          <label>Pengguna<input placeholder="Nama atau email" value={f.q} onChange={set("q")} onKeyDown={(e) => e.key === "Enter" && terapkan()} /></label>
          <label>Aksi<select value={f.aksi} onChange={set("aksi")}><option value="">Semua</option>{Object.entries(AKSI).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <label>Dari tanggal<input type="date" value={f.dari} onChange={set("dari")} /></label>
          <label>Sampai tanggal<input type="date" value={f.sampai} onChange={set("sampai")} /></label>
          <button className="btn pri sm" onClick={terapkan}>Terapkan</button>
          <button className="btn sm" onClick={reset}>Reset</button>
        </div>
      </Card>
      <div className="card" style={{ padding: 0 }}>
        {data.items.length === 0 ? <Empty>Belum ada aktivitas yang cocok.</Empty> : (
          <div className="tw"><table>
            <thead><tr><th>WAKTU</th><th>PENGGUNA</th><th>AKSI</th><th>OBJEK</th></tr></thead>
            <tbody>{data.items.map((r) => (
              <tr key={r.id_log}>
                <td>{waktu(r.waktu)}</td>
                <td><b>{r.nama}</b><div className="mut">{r.email}</div></td>
                <td><Badge tone={TONE[r.jenis_aksi]}>{AKSI[r.jenis_aksi] || r.jenis_aksi}</Badge></td>
                <td>{r.jenis_objek} <span className="code">#{r.id_objek}</span></td>
              </tr>))}</tbody>
          </table></div>
        )}
        <div className="pager">
          <span>Halaman {page} dari {maks} ({data.total} catatan)</span>
          <span style={{ display: "flex", gap: ".5rem" }}>
            <button className="btn sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Sebelumnya</button>
            <button className="btn sm" disabled={page >= maks} onClick={() => setPage(page + 1)}>Berikutnya</button>
          </span>
        </div>
      </div>
    </>
  );
}
