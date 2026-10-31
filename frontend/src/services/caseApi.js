async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error("Could not reach the MySQL case API. Start the backend on port 5001.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}

export const caseApi = {
  health: () => request("/api/health"),
  list: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.status) params.set("status", filters.status);
    const suffix = params.size ? `?${params.toString()}` : "";
    return request(`/api/cases${suffix}`);
  },
  get: (caseId) => request(`/api/cases/${caseId}`),
  create: (payload) => request("/api/cases", { method: "POST", body: JSON.stringify(payload) }),
  update: (caseId, payload) => request(`/api/cases/${caseId}`, { method: "PUT", body: JSON.stringify(payload) }),
  remove: (caseId) => request(`/api/cases/${caseId}`, { method: "DELETE" }),
};

export const authApi = {
  session: () => request("/api/auth/session"),
  login: (credentials) => request("/api/auth/login", { method: "POST", body: JSON.stringify(credentials) }),
  register: (credentials) => request("/api/auth/register", { method: "POST", body: JSON.stringify(credentials) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
};
