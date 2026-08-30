"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/app-state";
import { SectionHeader } from "./CountPill";

export function BookmarkList() {
  const { bookmarks, toggleBookmark } = useAppState();

  return (
    <div>
      <SectionHeader title="Bookmarked" count={bookmarks.length} />
      {bookmarks.length === 0 ? (
        <p className="text-xs text-muted-foreground">No saved spots yet — bookmark a card to see it here.</p>
      ) : (
        <ul className="space-y-1">
          {bookmarks.map((spot) => (
            <li
              key={spot.id}
              className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-sidebar-accent"
            >
              <div className="min-w-0 text-sm">
                <span className="font-medium">{spot.name}</span>
                <span className="text-muted-foreground"> · {spot.neighborhood}</span>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 shrink-0"
                aria-label={`Remove ${spot.name} from bookmarks`}
                title={`Remove ${spot.name} from bookmarks`}
                onClick={() => toggleBookmark(spot)}
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
