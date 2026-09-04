"use client";

import { AlertTriangle, Footprints, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/app-state";
import { SectionHeader } from "./CountPill";

export function ItineraryList() {
  const { itinerary, removeFromItinerary } = useAppState();

  return (
    <div>
      <SectionHeader title="Itinerary" count={itinerary.length} />
      {itinerary.length === 0 ? (
        <p className="text-xs text-muted-foreground">No stops added yet — use &ldquo;+ Itinerary&rdquo; on a card.</p>
      ) : (
        <ul>
          {itinerary.map((stop, idx) => (
            <li key={stop.spot.id}>
              <div className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-sidebar-accent">
                <div className="min-w-0 text-sm">
                  <span className="font-medium">
                    {idx + 1}. {stop.spot.name}
                  </span>
                  <div className="text-xs text-muted-foreground">
                    {stop.arrival_time} – {stop.departure_time}
                  </div>
                  {stop.timing_warning && (
                    <div className="mt-0.5 flex items-center gap-1 text-xs text-[color:var(--chart-3)]">
                      <AlertTriangle className="size-3 shrink-0" /> {stop.timing_warning}
                    </div>
                  )}
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  className="size-7 shrink-0"
                  aria-label={`Remove ${stop.spot.name} from itinerary`}
                  title={`Remove ${stop.spot.name} from itinerary`}
                  onClick={() => removeFromItinerary(stop.spot.id)}
                >
                  <X className="size-3.5" />
                </Button>
              </div>
              {stop.travel_to_next_minutes != null && (
                <div className="flex items-center gap-1.5 pl-3 py-1 text-xs text-muted-foreground">
                  <Footprints className="size-3.5" /> {stop.travel_to_next_minutes} min walk
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
