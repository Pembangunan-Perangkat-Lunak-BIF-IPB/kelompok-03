// Sesi pengguna dan "analisis aktif" (id_analisis yang sedang dikerjakan di alur 1-5).
const K = { token: "gvc_token", user: "gvc_user", active: "gvc_analisis" };
const ok = () => typeof window !== "undefined";

export const getToken = () => (ok() ? localStorage.getItem(K.token) : null);
export const getUser = () => { try { return ok() ? JSON.parse(localStorage.getItem(K.user)) : null; } catch { return null; } };
export function setSession(token, user) { localStorage.setItem(K.token, token); localStorage.setItem(K.user, JSON.stringify(user)); }
export function clearSession() { Object.values(K).forEach((k) => localStorage.removeItem(k)); window.dispatchEvent(new Event("gvc:active")); }

export const getActive = () => (ok() ? Number(localStorage.getItem(K.active)) || null : null);
export function setActive(id) {
  if (id) localStorage.setItem(K.active, String(id)); else localStorage.removeItem(K.active);
  window.dispatchEvent(new Event("gvc:active"));
}
