"use client";

import { Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useAppState } from "@/lib/app-state";

export function ImportPopover() {
  const { hasCustomDataset, activeSpotCount, importFile, removeUploadedDataset } = useAppState();
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setBusy(true);
    setStatus(null);
    const result = await importFile(file);
    setStatus({ ok: result.ok, message: result.message });
    setBusy(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <Popover>
      <PopoverTrigger className={buttonVariants({ variant: "outline", className: "gap-1.5" })}>
        <Upload className="size-4" /> Import
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        {hasCustomDataset && (
          <>
            <p className="text-sm text-muted-foreground">
              Using {activeSpotCount} uploaded spots instead of the demo dataset.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="w-full mt-2 gap-1.5"
              onClick={() => removeUploadedDataset()}
            >
              <X className="size-3.5" /> Remove uploaded data (use demo dataset)
            </Button>
            <div className="my-3 h-px bg-border" />
          </>
        )}

        <p className="text-sm font-medium mb-1">Import your own places</p>
        <p className="text-xs text-muted-foreground mb-2">
          CSV: a Google Maps list export (Title/URL columns) — geocoding takes ~1 sec/row, so a large list can take a
          couple minutes. JSON: a Google Takeout &ldquo;Saved Places.json&rdquo; export — imports instantly.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
          className="text-sm w-full file:mr-2 file:rounded-md file:border-0 file:bg-secondary file:px-2 file:py-1 file:text-xs"
        />
        {busy && <p className="text-xs text-muted-foreground mt-2">Importing… this can take a couple minutes for CSV.</p>}
        {status && (
          <p className={`text-xs mt-2 ${status.ok ? "text-primary" : "text-destructive"}`}>{status.message}</p>
        )}
      </PopoverContent>
    </Popover>
  );
}
