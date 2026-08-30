import type { ChatMessage, ChatResponse, ImportResult, Spot, SessionState } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include", // send/receive the session_id cookie cross-origin
    headers: {
      ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON, keep statusText
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getSession: () => request<SessionState>("/session"),
  resetSession: () => request<{ status: string }>("/session/reset", { method: "POST" }),

  getSpots: (q: string, category: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category && category !== "All") params.set("category", category);
    const qs = params.toString();
    return request<Spot[]>(`/spots${qs ? `?${qs}` : ""}`);
  },

  chat: (query: string, history: ChatMessage[]) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ query, history }),
    }),

  getBookmarks: () => request<Spot[]>("/bookmarks"),
  addBookmark: (spot: Spot) => request<Spot[]>("/bookmarks", { method: "POST", body: JSON.stringify(spot) }),
  removeBookmark: (spotId: string) => request<Spot[]>(`/bookmarks/${encodeURIComponent(spotId)}`, { method: "DELETE" }),
  resetBookmarks: () => request<Spot[]>("/bookmarks/reset", { method: "POST" }),

  getItinerary: () => request<Spot[]>("/itinerary"),
  addItineraryStop: (spot: Spot) => request<Spot[]>("/itinerary", { method: "POST", body: JSON.stringify(spot) }),
  removeItineraryStop: (spotId: string) => request<Spot[]>(`/itinerary/${encodeURIComponent(spotId)}`, { method: "DELETE" }),
  resetItinerary: () => request<Spot[]>("/itinerary/reset", { method: "POST" }),

  importFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<ImportResult>("/import", { method: "POST", body: formData });
  },
  resetImport: () => request<{ status: string }>("/import/reset", { method: "POST" }),
};
