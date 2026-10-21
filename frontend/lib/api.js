// Lapisan API. `api()` dipertahankan; `svc` dipakai semua halaman.
// NEXT_PUBLIC_USE_MOCK=true -> data tiruan (lib/mock.js); false -> FastAPI (docs/API_CONTRACT.md).
import { getToken } from "./session";
import { mock } from "./mock";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

const msg = (body, status) => {
  const d = body?.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join("; ") : `Permintaan gagal (${status})`;
};

export async function api(path, options = {}) {
  const token = getToken();
  const isForm = options.body instanceof FormData;
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    ...options,
    headers: { ...(isForm ? {} : { "Content-Type": "application/json" }), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.includes("/auth/login")) { localStorage.clear(); window.location.href = "/login"; }
  if (res.status === 204) return null;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(msg(body, res.status));
  return body;
}
const J = (o) => JSON.stringify(o);
const qs = (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== "" && v != null)).toString();

function upload(path, form, onProgress) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest(); x.open("POST", BASE + path);
    const t = getToken(); if (t) x.setRequestHeader("Authorization", `Bearer ${t}`);
    x.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((e.loaded / e.total) * 100));
    x.onload = () => { let b = null; try { b = JSON.parse(x.responseText); } catch {} x.status < 300 ? resolve(b) : reject(new Error(msg(b, x.status))); };
    x.onerror = () => reject(new Error("Koneksi ke server gagal saat mengunggah."));
    x.send(form);
  });
}
async function download(path, filename) {
  const res = await fetch(BASE + path, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error(msg(await res.json().catch(() => null), res.status));
  return { blob: await res.blob(), filename };
}

const real = {
  login: (email, password) => api("/api/auth/login", { method: "POST", body: J({ email, password }) }),
  buatSampel(meta, files, onProgress) {
    const f = new FormData(); Object.entries(meta).forEach(([k, v]) => f.append(k, v));
    f.append("fastq_r1", files[0]); if (files[1]) f.append("fastq_r2", files[1]);
    return upload("/api/sampel", f, onProgress); // -> analisis (draf) + sampel
  },
  listReferensi: (jenis) => api(`/api/referensi?${qs({ jenis })}`),
  unggahReferensi({ nama_referensi, jenis, file }) { const f = new FormData(); f.append("nama_referensi", nama_referensi || file.name); f.append("jenis", jenis); f.append("berkas", file); return api("/api/referensi", { method: "POST", body: f }); },
  hapusReferensi: (id) => api(`/api/referensi/${id}`, { method: "DELETE" }),
  listAnalisis: () => api("/api/analisis"),
  getAnalisis: (id) => api(`/api/analisis/${id}`),
  simpanKonfigurasi: (id, b) => api(`/api/analisis/${id}`, { method: "PATCH", body: J(b) }),
  jalankan: (id) => api(`/api/analisis/${id}/jalankan`, { method: "POST" }),
  getLog: (id) => api(`/api/analisis/${id}/log`),
  salinAnalisis: (id) => api(`/api/analisis/${id}/salin`, { method: "POST" }),
  ringkasan: (id) => api(`/api/analisis/${id}/ringkasan`),
  varianAnalisis: (id, page, size) => api(`/api/analisis/${id}/varian?${qs({ page, size })}`),
  kunci: (id) => api(`/api/analisis/${id}/kunci`, { method: "POST" }),
  publikasi: (id) => api(`/api/analisis/${id}/publikasi`, { method: "POST" }),
  unduh: (id, format) => download(`/api/analisis/${id}/unduh?format=${format}`, `analisis-${id}.${format}`),
  cariVarian: (p) => api(`/api/varian?${qs(p)}`),
  detailVarian: (id) => api(`/api/varian/${id}`),
  listPengguna: () => api("/api/pengguna"),
  simpanPengguna: (id, b) => (id ? api(`/api/pengguna/${id}`, { method: "PATCH", body: J(b) }) : api("/api/pengguna", { method: "POST", body: J(b) })),
};

export const svc = USE_MOCK ? mock : real;
export function saveBlob({ blob, filename }) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
