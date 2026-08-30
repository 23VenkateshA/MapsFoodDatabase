"use client";

import { UtensilsCrossed } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
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
  const { ready, bootstrapError, viewMode, lastSpots, hasCustomDataset, activeSpotCount, demoSpotCount } =
    useAppState();
  const [browseSpots, setBrowseSpots] = useState<Spot[]>([]);

  const mapSpots = viewMode === "browse" ? browseSpots : lastSpots;

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

        <div className="mt-4">
          <ModeToggle />
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            {viewMode === "browse" ? (
              <SpotsBrowser onSpotsChange={setBrowseSpots} demoSpotCount={demoSpotCount} />
            ) : (
              <ChatPanel />
            )}
          </div>
          <div>
            <h2 className="text-[22px] font-semibold mb-2">Map</h2>
            <MapView spots={mapSpots} />
          </div>
        </div>
      </main>
    </div>
  );
}
