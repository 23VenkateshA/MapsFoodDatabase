"use client";

import { X } from "lucide-react";
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
        <ul className="space-y-1">
          {itinerary.map((spot, idx) => (
            <li
              key={spot.id}
              className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-sidebar-accent"
            >
              <div className="min-w-0 text-sm">
                <span className="font-medium">
                  {idx + 1}. {spot.name}
                </span>
                <div className="text-xs text-muted-foreground">
                  {spot.itinerary_context.best_time_slot} · ~{spot.itinerary_context.estimated_duration_min} min
                </div>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 shrink-0"
                aria-label={`Remove ${spot.name} from itinerary`}
                title={`Remove ${spot.name} from itinerary`}
                onClick={() => removeFromItinerary(spot.id)}
              >
                <X className="size-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
