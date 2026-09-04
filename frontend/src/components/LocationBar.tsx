"use client";

import { Check, Home, MapPin, Plus, X } from "lucide-react";
import { useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useAppState } from "@/lib/app-state";

const RADIUS_PRESETS_MILES = [0.5, 1, 2];

export function LocationBar() {
  const {
    addresses,
    activeAddressId,
    setActiveAddressId,
    radiusMiles,
    setRadiusMiles,
    addAddress,
    removeAddress,
    setDefaultAddress,
  } = useAppState();
  const [label, setLabel] = useState("Home");
  const [addressText, setAddressText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const active = addresses.find((a) => a.id === activeAddressId) ?? null;

  async function handleAdd() {
    if (!addressText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await addAddress({ label: label.trim() || "Address", address: addressText.trim() });
      setActiveAddressId(created.id);
      setAddressText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not find that address.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Popover>
        <PopoverTrigger
          className={buttonVariants({ variant: active ? "default" : "outline", size: "sm", className: "gap-1.5" })}
        >
          <MapPin className="size-3.5" />
          {active ? `Near: ${active.label}` : "Search near…"}
        </PopoverTrigger>
        <PopoverContent className="w-80" align="start">
          {addresses.length > 0 && (
            <>
              <p className="text-sm font-medium mb-1">Saved addresses</p>
              <ul className="space-y-1 mb-2">
                {addresses.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-secondary/60"
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left text-sm"
                      onClick={() => setActiveAddressId(a.id)}
                    >
                      <span className="font-medium">{a.label}</span>
                      {a.is_default && <span className="text-xs text-muted-foreground"> · default</span>}
                      <div className="truncate text-xs text-muted-foreground">{a.address}</div>
                    </button>
                    <div className="flex shrink-0 items-center gap-1">
                      {activeAddressId === a.id && <Check className="size-3.5 text-primary" />}
                      {!a.is_default && (
                        <Button
                          size="icon-xs"
                          variant="ghost"
                          title="Set as default"
                          onClick={() => setDefaultAddress(a.id)}
                        >
                          <Home className="size-3" />
                        </Button>
                      )}
                      <Button size="icon-xs" variant="ghost" title="Remove" onClick={() => removeAddress(a.id)}>
                        <X className="size-3" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
              {active && (
                <Button size="sm" variant="outline" className="w-full mb-2" onClick={() => setActiveAddressId(null)}>
                  Clear anchor
                </Button>
              )}
              <div className="h-px bg-border my-2" />
            </>
          )}

          <p className="text-sm font-medium mb-1">Add an address</p>
          <div className="flex gap-1.5 mb-1.5">
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Home" className="w-24" />
            <Input
              value={addressText}
              onChange={(e) => setAddressText(e.target.value)}
              placeholder="123 Main St, New York, NY"
            />
          </div>
          <Button size="sm" className="w-full gap-1.5" disabled={busy || !addressText.trim()} onClick={() => void handleAdd()}>
            <Plus className="size-3.5" /> {busy ? "Finding…" : "Save & use"}
          </Button>
          {error && <p className="text-xs text-destructive mt-1.5">{error}</p>}
        </PopoverContent>
      </Popover>

      {active && (
        <div className="flex items-center gap-1.5">
          {RADIUS_PRESETS_MILES.map((mi) => (
            <Button
              key={mi}
              size="sm"
              variant={radiusMiles === mi ? "default" : "outline"}
              onClick={() => setRadiusMiles(radiusMiles === mi ? null : mi)}
            >
              {mi}mi
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
