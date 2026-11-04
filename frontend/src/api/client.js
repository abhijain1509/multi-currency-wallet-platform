const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

// The JWT lives only in an httpOnly cookie set by the backend — it is never
// stored in or read from JS. We persist only non-sensitive display info so the
// UI can gate routes after a refresh.
export function setSession(user) {
  localStorage.setItem("user", JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem("user");
}

export function getUser() {
  const raw = localStorage.getItem("user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    // Corrupted storage shouldn't crash the app on load.
    clearSession();
    return null;
  }
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  const resp = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    // Send/receive the httpOnly auth cookie (same-origin via the proxy).
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  // An expired/invalid session on an authenticated call: clear local state and
  // send the user back to login instead of leaving them on a broken screen.
  if (resp.status === 401 && auth) {
    clearSession();
    if (window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    throw new Error("Your session has expired. Please log in again.");
  }
  const data = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) {
    const detail = data?.detail || resp.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

async function uploadFile(path, file) {
  const formData = new FormData();
  formData.append("file", file);
  // No Content-Type header: the browser sets the multipart boundary itself.
  const resp = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (resp.status === 401) {
    clearSession();
    if (window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    throw new Error("Your session has expired. Please log in again.");
  }
  const data = await resp.json().catch(() => null);
  if (!resp.ok) {
    const detail = data?.detail || resp.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  signup: (payload) => request("/auth/signup", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),
  logout: () => request("/auth/logout", { method: "POST", auth: false }),
  profile: () => request("/auth/profile"),
  updateProfile: (payload) => request("/auth/profile", { method: "PATCH", body: payload }),
  uploadPhoto: (file) => uploadFile("/auth/profile/photo", file),
  listWallets: () => request("/wallets"),
  credit: (payload) => request("/wallets/credit", { method: "POST", body: payload }),
  debit: (payload) => request("/wallets/debit", { method: "POST", body: payload }),
  rates: () => request("/exchange/rates"),
  transfer: (payload) => request("/transfers", { method: "POST", body: payload }),
  transactions: (query = "") => request(`/transactions${query}`),
};
