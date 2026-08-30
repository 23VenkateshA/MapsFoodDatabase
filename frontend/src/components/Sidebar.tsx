"use client";

import { UtensilsCrossed } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAppState } from "@/lib/app-state";
import { BookmarkList } from "./BookmarkList";
import { ItineraryList } from "./ItineraryList";

export function Sidebar() {
  const { clearBookmarks, clearItinerary, resetSession } = useAppState();

  return (
    <aside className="w-full lg:w-64 shrink-0 border-r border-sidebar-border bg-sidebar px-4 py-5">
      <h2 className="flex items-center gap-2 text-lg font-bold mb-4">
        <UtensilsCrossed className="size-5" />
        Your NYC Concierge
      </h2>

      <BookmarkList />
      <Separator className="my-4" />
      <ItineraryList />
      <Separator className="my-4" />

      <div className="grid grid-cols-2 gap-2">
        <Button variant="outline" size="sm" onClick={() => clearBookmarks()}>
          Clear bookmarks
        </Button>
        <Button variant="outline" size="sm" onClick={() => clearItinerary()}>
          Clear itinerary
        </Button>
      </div>
      <Button className="w-full mt-2" size="sm" onClick={() => resetSession()}>
        Reset entire session
      </Button>
    </aside>
  );
}
