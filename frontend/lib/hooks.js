"use client";
import { useCallback, useEffect, useState } from "react";
import { svc } from "./api";
import { getActive } from "./session";

// Memuat analisis aktif; polling opsional (ms) selama status menunggu/berjalan.
export function useAnalisis(poll = 0) {
  const [id, setId] = useState(undefined);
  const [a, setA] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { const s = () => setId(getActive()); s(); window.addEventListener("gvc:active", s); return () => window.removeEventListener("gvc:active", s); }, []);
  const reload = useCallback(async () => {
    if (!id) { setA(null); return null; }
    try { const d = await svc.getAnalisis(id); setA(d); setError(""); return d; } catch (e) { setError(e.message); return null; }
  }, [id]);
  useEffect(() => { reload(); }, [reload]);
  useEffect(() => {
    if (!poll || !a || !["menunggu", "berjalan"].includes(a.status)) return;
    const t = setInterval(reload, poll); return () => clearInterval(t);
  }, [poll, a, reload]);
  return { id, a, setA, error, reload, loading: id === undefined || (id && !a && !error) };
}
