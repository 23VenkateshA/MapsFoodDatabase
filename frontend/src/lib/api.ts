import type { Address, AddressIn, ChatMessage, ChatResponse, ImportResult, ItineraryStop, Spot, SessionState } from "./types";

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

export interface RadiusSearch {
  addressId?: string;
  radiusMiles?: number | null;
  sort?: "distance";
}

export interface ChatLocationContext {
  label: string;
  lat: number;
  lng: number;
  radiusMiles: number | null;
}

export const api = {
  getSession: () => request<SessionState>("/session"),
  resetSession: () => request<{ status: string }>("/session/reset", { method: "POST" }),

  getSpots: (q: string, category: string, radius?: RadiusSearch) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category && category !== "All") params.set("category", category);
    if (radius?.addressId) params.set("address_id", radius.addressId);
    if (radius?.radiusMiles != null) params.set("radius_miles", String(radius.radiusMiles));
    if (radius?.sort) params.set("sort", radius.sort);
    const qs = params.toString();
    return request<Spot[]>(`/spots${qs ? `?${qs}` : ""}`);
  },

  chat: (query: string, history: ChatMessage[], location?: ChatLocationContext | null) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        query,
        history,
        near_label: location?.label ?? null,
        near_lat: location?.lat ?? null,
        near_lng: location?.lng ?? null,
        radius_miles: location?.radiusMiles ?? null,
      }),
    }),

  getBookmarks: () => request<Spot[]>("/bookmarks"),
  addBookmark: (spot: Spot) => request<Spot[]>("/bookmarks", { method: "POST", body: JSON.stringify(spot) }),
  removeBookmark: (spotId: string) => request<Spot[]>(`/bookmarks/${encodeURIComponent(spotId)}`, { method: "DELETE" }),
  resetBookmarks: () => request<Spot[]>("/bookmarks/reset", { method: "POST" }),

  getItinerary: () => request<ItineraryStop[]>("/itinerary"),
  addItineraryStop: (spot: Spot) => request<ItineraryStop[]>("/itinerary", { method: "POST", body: JSON.stringify(spot) }),
  removeItineraryStop: (spotId: string) =>
    request<ItineraryStop[]>(`/itinerary/${encodeURIComponent(spotId)}`, { method: "DELETE" }),
  resetItinerary: () => request<ItineraryStop[]>("/itinerary/reset", { method: "POST" }),

  getAddresses: () => request<Address[]>("/addresses"),
  addAddress: (payload: AddressIn) =>
    request<Address>("/addresses", { method: "POST", body: JSON.stringify(payload) }),
  removeAddress: (addressId: string) =>
    request<Address[]>(`/addresses/${encodeURIComponent(addressId)}`, { method: "DELETE" }),
  setDefaultAddress: (addressId: string) =>
    request<Address[]>(`/addresses/${encodeURIComponent(addressId)}/default`, { method: "PUT" }),

  importFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<ImportResult>("/import", { method: "POST", body: formData });
  },
  resetImport: () => request<{ status: string }>("/import/reset", { method: "POST" }),
};
