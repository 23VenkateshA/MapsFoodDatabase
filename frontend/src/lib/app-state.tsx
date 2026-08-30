"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import type { ChatMessage, Spot, ViewMode } from "./types";

interface AppState {
  // Bootstrap / loading
  ready: boolean;
  bootstrapError: string | null;

  // Bookmarks
  bookmarks: Spot[];
  isBookmarked: (spotId: string) => boolean;
  toggleBookmark: (spot: Spot) => Promise<void>;
  clearBookmarks: () => Promise<void>;

  // Itinerary
  itinerary: Spot[];
  isInItinerary: (spotId: string) => boolean;
  addToItinerary: (spot: Spot) => Promise<void>;
  removeFromItinerary: (spotId: string) => Promise<void>;
  clearItinerary: () => Promise<void>;

  // Chat
  messages: ChatMessage[];
  lastSpots: Spot[];
  lastSummary: string;
  lastFilters: string[];
  chatLoading: boolean;
  chatError: string | null;
  sendQuery: (query: string) => Promise<void>;

  // View / dataset
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  hasCustomDataset: boolean;
  activeSpotCount: number;
  demoSpotCount: number;

  // Import
  importFile: (file: File) => Promise<{ message: string; ok: boolean }>;
  removeUploadedDataset: () => Promise<void>;

  // Session
  resetSession: () => Promise<void>;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);

  const [bookmarks, setBookmarks] = useState<Spot[]>([]);
  const [itinerary, setItinerary] = useState<Spot[]>([]);
  const [hasCustomDataset, setHasCustomDataset] = useState(false);
  const [activeSpotCount, setActiveSpotCount] = useState(0);
  const [demoSpotCount, setDemoSpotCount] = useState(0);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastSpots, setLastSpots] = useState<Spot[]>([]);
  const [lastSummary, setLastSummary] = useState("");
  const [lastFilters, setLastFilters] = useState<string[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>("chat");

  useEffect(() => {
    api
      .getSession()
      .then((s) => {
        setBookmarks(s.bookmarks);
        setItinerary(s.itinerary);
        setHasCustomDataset(s.has_custom_dataset);
        setActiveSpotCount(s.active_spot_count);
        setDemoSpotCount(s.demo_spot_count);
        setReady(true);
      })
      .catch((err) => {
        setBootstrapError(err instanceof Error ? err.message : "Could not reach the API.");
        setReady(true);
      });
  }, []);

  const isBookmarked = useCallback((spotId: string) => bookmarks.some((b) => b.id === spotId), [bookmarks]);
  const isInItinerary = useCallback((spotId: string) => itinerary.some((s) => s.id === spotId), [itinerary]);

  const toggleBookmark = useCallback(
    async (spot: Spot) => {
      if (isBookmarked(spot.id)) {
        setBookmarks(await api.removeBookmark(spot.id));
      } else {
        setBookmarks(await api.addBookmark(spot));
      }
    },
    [isBookmarked],
  );

  const clearBookmarks = useCallback(async () => {
    setBookmarks(await api.resetBookmarks());
  }, []);

  const addToItinerary = useCallback(async (spot: Spot) => {
    setItinerary(await api.addItineraryStop(spot));
  }, []);

  const removeFromItinerary = useCallback(async (spotId: string) => {
    setItinerary(await api.removeItineraryStop(spotId));
  }, []);

  const clearItinerary = useCallback(async () => {
    setItinerary(await api.resetItinerary());
  }, []);

  const sendQuery = useCallback(
    async (query: string) => {
      setChatLoading(true);
      setChatError(null);
      const nextMessages: ChatMessage[] = [...messages, { role: "user", content: query }];
      setMessages(nextMessages);
      try {
        const result = await api.chat(query, messages);
        setLastSpots(result.spots);
        setLastSummary(result.summary);
        setLastFilters(result.quick_filters);
        setMessages([...nextMessages, { role: "assistant", content: result.summary }]);
      } catch (err) {
        setChatError(err instanceof Error ? err.message : "Something went wrong finding spots.");
      } finally {
        setChatLoading(false);
      }
    },
    [messages],
  );

  const importFile = useCallback(async (file: File) => {
    try {
      const result = await api.importFile(file);
      const session = await api.getSession();
      setHasCustomDataset(session.has_custom_dataset);
      setActiveSpotCount(session.active_spot_count);
      return { message: result.message, ok: true };
    } catch (err) {
      return { message: err instanceof Error ? err.message : "Import failed.", ok: false };
    }
  }, []);

  const removeUploadedDataset = useCallback(async () => {
    await api.resetImport();
    const session = await api.getSession();
    setHasCustomDataset(session.has_custom_dataset);
    setActiveSpotCount(session.active_spot_count);
  }, []);

  const resetSession = useCallback(async () => {
    await api.resetSession();
    const session = await api.getSession();
    setBookmarks(session.bookmarks);
    setItinerary(session.itinerary);
    setHasCustomDataset(session.has_custom_dataset);
    setActiveSpotCount(session.active_spot_count);
    setMessages([]);
    setLastSpots([]);
    setLastSummary("");
    setLastFilters([]);
  }, []);

  const value = useMemo<AppState>(
    () => ({
      ready,
      bootstrapError,
      bookmarks,
      isBookmarked,
      toggleBookmark,
      clearBookmarks,
      itinerary,
      isInItinerary,
      addToItinerary,
      removeFromItinerary,
      clearItinerary,
      messages,
      lastSpots,
      lastSummary,
      lastFilters,
      chatLoading,
      chatError,
      sendQuery,
      viewMode,
      setViewMode,
      hasCustomDataset,
      activeSpotCount,
      demoSpotCount,
      importFile,
      removeUploadedDataset,
      resetSession,
    }),
    [
      ready, bootstrapError, bookmarks, isBookmarked, toggleBookmark, clearBookmarks,
      itinerary, isInItinerary, addToItinerary, removeFromItinerary, clearItinerary,
      messages, lastSpots, lastSummary, lastFilters, chatLoading, chatError, sendQuery,
      viewMode, hasCustomDataset, activeSpotCount, demoSpotCount, importFile,
      removeUploadedDataset, resetSession,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
