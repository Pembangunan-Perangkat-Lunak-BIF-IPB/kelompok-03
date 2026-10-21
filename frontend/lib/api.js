// Pemanggil API backend. Alamat diatur lewat NEXT_PUBLIC_API_URL.
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || `Permintaan gagal (${res.status})`);
  return body;
}
