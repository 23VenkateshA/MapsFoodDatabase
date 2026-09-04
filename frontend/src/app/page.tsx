"use client";

import { UtensilsCrossed } from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { LocationBar } from "@/components/LocationBar";
import { ModeToggle } from "@/components/ModeToggle";
import { Sidebar } from "@/components/Sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { SpotsBrowser } from "@/components/SpotsBrowser";
import { useAppState } from "@/lib/app-state";
import type { Spot } from "@/lib/types";

// react-leaflet touches `window` at import time, so it can never run during
// Next.js's server render - this is the client-only equivalent of the
// Streamlit constraint that st_folium's iframe only exists in the browser.
const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), {
  ssr: false,
  loading: () => <Skeleton className="h-[560px] w-full rounded-lg" />,
});

export default function Home() {
  const {
    ready,
    bootstrapError,
    viewMode,
    lastSpots,
    hasCustomDataset,
    activeSpotCount,
    demoSpotCount,
    addresses,
    activeAddressId,
    radiusMiles,
    itinerary,
    selectedSpotId,
    setSelectedSpotId,
  } = useAppState();
  const [browseSpots, setBrowseSpots] = useState<Spot[]>([]);
  const mapColumnRef = useRef<HTMLDivElement>(null);

  const mapSpots = viewMode === "browse" ? browseSpots : lastSpots;
  const activeAddress = addresses.find((a) => a.id === activeAddressId) ?? null;
  const itineraryCoords = itinerary
    .map((stop) => stop.spot.coordinates)
    .filter((c): c is { lat: number; lng: number } => c.lat != null && c.lng != null);

  useEffect(() => {
    if (selectedSpotId && typeof window !== "undefined" && window.innerWidth < 1024) {
      mapColumnRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [selectedSpotId]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground text-sm">
        Loading…
      </div>
    );
  }

  if (bootstrapError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center">
        <div>
          <p className="font-semibold text-destructive mb-1">Couldn&rsquo;t reach the API</p>
          <p className="text-sm text-muted-foreground max-w-md">{bootstrapError}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Is the FastAPI backend running at {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}?
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row flex-1">
      <Sidebar />

      <main className="flex-1 p-4 sm:p-6 max-w-[1400px] mx-auto w-full">
        <h1 className="flex items-center gap-2 text-[28px] font-bold">
          <UtensilsCrossed className="size-7" />
          NYC Dining Concierge
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          {hasCustomDataset
            ? `${activeSpotCount} spots from your uploaded list — chat for curated picks, or search and filter.`
            : `${demoSpotCount} saved NYC spots — chat for curated picks, or search and filter the full list.`}
        </p>

        <div className="mt-4 flex flex-col gap-3">
          <ModeToggle />
          <LocationBar />
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            {viewMode === "browse" ? (
              <SpotsBrowser onSpotsChange={setBrowseSpots} demoSpotCount={demoSpotCount} />
            ) : (
              <ChatPanel />
            )}
          </div>
          <div ref={mapColumnRef}>
            <h2 className="text-[22px] font-semibold mb-2">Map</h2>
            <MapView
              spots={mapSpots}
              anchor={activeAddress ? { lat: activeAddress.lat, lng: activeAddress.lng, label: activeAddress.label } : null}
              radiusMiles={activeAddress ? radiusMiles : null}
              itineraryStops={itineraryCoords}
              selectedSpotId={selectedSpotId}
              onSelectSpot={setSelectedSpotId}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
