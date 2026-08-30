// Mirrors backend/models/schemas.py exactly - one field for one field.

export interface Coordinates {
  lat: number | null;
  lng: number | null;
}

export interface Links {
  google_maps: string;
  reservation_url: string | null;
  reservation_platform: string | null;
}

export interface ItineraryContext {
  best_time_slot: string;
  estimated_duration_min: number;
}

export interface Spot {
  id: string;
  name: string;
  source: "saved" | "fallback";
  is_bookmarked: boolean;
  category?: string | null;
  neighborhood: string;
  cuisine: string[];
  price_level: string;
  rating: number | null;
  match_highlight: string;
  coordinates: Coordinates;
  links: Links;
  itinerary_context: ItineraryContext;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  summary: string;
  fallback_triggered: boolean;
  spots: Spot[];
  quick_filters: string[];
}

export interface SessionState {
  bookmarks: Spot[];
  itinerary: Spot[];
  has_custom_dataset: boolean;
  active_spot_count: number;
  demo_spot_count: number;
}

export interface ImportResult {
  spots_imported: number;
  skipped: number;
  message: string;
}

export type ViewMode = "chat" | "browse";
export type CategoryFilter = "All" | "Bar" | "Cafe" | "Eats";
