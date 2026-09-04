"use client";

import { Bookmark, BookmarkCheck, Check, ExternalLink, Footprints, Lightbulb, MapPin, Plus, Sparkles, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAppState } from "@/lib/app-state";
import type { Spot } from "@/lib/types";

export function SpotCard({ spot }: { spot: Spot }) {
  const { isBookmarked, toggleBookmark, isInItinerary, addToItinerary, selectedSpotId, setSelectedSpotId } =
    useAppState();
  const bookmarked = isBookmarked(spot.id);
  const inItinerary = isInItinerary(spot.id);
  const isSelected = selectedSpotId === spot.id;

  return (
    <div
      className={`rounded-lg bg-card p-3 sm:p-4 border-l-2 transition-colors hover:bg-secondary/60 ${
        isSelected ? "border-l-primary bg-secondary/50" : "border-l-transparent"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
          <button
            type="button"
            onClick={() => setSelectedSpotId(isSelected ? null : spot.id)}
            className="text-left font-semibold text-foreground hover:text-primary hover:underline underline-offset-2"
          >
            {spot.name}
          </button>
          <span className="text-muted-foreground">·</span>
          <span className="inline-flex items-center gap-1 tabular-nums font-semibold">
            <Star className="size-3.5" /> {spot.rating ?? "—"}
          </span>
          <span className="text-muted-foreground">·</span>
          <span>{spot.price_level}</span>
          <span className="text-muted-foreground">·</span>
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <MapPin className="size-3.5" /> {spot.neighborhood || "—"}
          </span>
          {spot.walk_minutes != null && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="inline-flex items-center gap-1 text-muted-foreground">
                <Footprints className="size-3.5" /> {spot.walk_minutes} min
              </span>
            </>
          )}
        </div>
        {spot.source === "saved" ? (
          <Badge className="shrink-0 gap-1 bg-primary/15 text-primary hover:bg-primary/15">
            <Bookmark className="size-3" /> Saved
          </Badge>
        ) : (
          <Badge variant="secondary" className="shrink-0 gap-1">
            <Sparkles className="size-3" /> Curated Pick
          </Badge>
        )}
      </div>

      {spot.cuisine.length > 0 && (
        <p className="mt-1 text-xs text-muted-foreground">{spot.cuisine.join(", ")}</p>
      )}

      {spot.match_highlight && (
        <p className="mt-2 flex items-start gap-1.5 text-sm">
          <Lightbulb className="size-3.5 mt-0.5 shrink-0" />
          <span>{spot.match_highlight}</span>
        </p>
      )}

      {spot.itinerary_context?.best_time_slot && (
        <p className="mt-1 text-xs text-muted-foreground">
          Best time: {spot.itinerary_context.best_time_slot} · ~{spot.itinerary_context.estimated_duration_min} min
        </p>
      )}

      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Button
          size="sm"
          variant={bookmarked ? "default" : "outline"}
          onClick={() => toggleBookmark(spot)}
          className="gap-1.5"
        >
          {bookmarked ? <BookmarkCheck className="size-3.5" /> : <Bookmark className="size-3.5" />}
          {bookmarked ? "Saved" : "Bookmark"}
        </Button>
        <a
          href={spot.links.google_maps || "https://maps.google.com"}
          target="_blank"
          rel="noreferrer"
          className={buttonVariants({ size: "sm", variant: "outline", className: "gap-1.5" })}
        >
          <ExternalLink className="size-3.5" /> Maps
        </a>
        {spot.links.reservation_url ? (
          <a
            href={spot.links.reservation_url}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ size: "sm", variant: "outline", className: "gap-1.5" })}
          >
            <ExternalLink className="size-3.5" /> {spot.links.reservation_platform || "Reserve"}
          </a>
        ) : (
          <span
            className={buttonVariants({
              size: "sm",
              variant: "outline",
              className: "gap-1.5 pointer-events-none opacity-50",
            })}
          >
            No reservation
          </span>
        )}
        <Button
          size="sm"
          variant={inItinerary ? "secondary" : "outline"}
          disabled={inItinerary}
          onClick={() => addToItinerary(spot)}
          className="gap-1.5"
        >
          {inItinerary ? <Check className="size-3.5" /> : <Plus className="size-3.5" />}
          {inItinerary ? "In itinerary" : "Itinerary"}
        </Button>
      </div>
    </div>
  );
}
