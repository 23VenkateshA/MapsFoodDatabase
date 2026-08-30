"use client";

import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { CategoryFilter, Spot } from "@/lib/types";
import { SectionHeader } from "./CountPill";
import { SpotCard } from "./SpotCard";

const CATEGORY_CHIPS: { label: string; value: CategoryFilter }[] = [
  { label: "All", value: "All" },
  { label: "Bars", value: "Bar" },
  { label: "Cafes", value: "Cafe" },
  { label: "Eats", value: "Eats" },
];

const CARD_LIMIT = 40;

export function SpotsBrowser({
  onSpotsChange,
  demoSpotCount,
}: {
  onSpotsChange: (spots: Spot[]) => void;
  demoSpotCount: number;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CategoryFilter>("All");
  const [spots, setSpots] = useState<Spot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getSpots(query, category)
      .then((result) => {
        if (cancelled) return;
        setSpots(result);
        onSpotsChange(result);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load spots.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, category]);

  return (
    <div>
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by name, neighborhood, or cuisine (e.g. tacos, East Village, bagels)"
      />

      <div className="mt-2 grid grid-cols-4 gap-2">
        {CATEGORY_CHIPS.map((c) => (
          <Button
            key={c.value}
            size="sm"
            variant={category === c.value ? "default" : "outline"}
            onClick={() => setCategory(c.value)}
          >
            {c.label}
          </Button>
        ))}
      </div>

      <div className="mt-6">
        <SectionHeader title="Browse" count={`${spots.length} of ${demoSpotCount}`} />

        {error && <p className="text-sm text-destructive">{error}</p>}

        {!error && loading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!error && !loading && spots.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-2 text-center text-muted-foreground py-10">
            <Search className="size-8" />
            <p className="text-sm">No spots match your search — try a different keyword or category.</p>
          </div>
        )}

        {!error && !loading && spots.length > 0 && (
          <>
            {spots.length > CARD_LIMIT && (
              <p className="text-xs text-muted-foreground mb-2">
                Showing the first {CARD_LIMIT} of {spots.length} matches — the map on the right still plots all of
                them. Narrow your search to see more cards.
              </p>
            )}
            <div className="space-y-3">
              {spots.slice(0, CARD_LIMIT).map((spot) => (
                <SpotCard key={spot.id} spot={spot} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
