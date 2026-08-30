"use client";

import { MessageCircle, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/app-state";
import { ImportPopover } from "./ImportPopover";

export function ModeToggle() {
  const { viewMode, setViewMode } = useAppState();

  return (
    <div className="flex gap-2">
      <Button
        variant={viewMode === "chat" ? "default" : "outline"}
        className="flex-1 gap-1.5"
        onClick={() => setViewMode("chat")}
      >
        <MessageCircle className="size-4" /> Concierge Chat
      </Button>
      <Button
        variant={viewMode === "browse" ? "default" : "outline"}
        className="flex-1 gap-1.5"
        onClick={() => setViewMode("browse")}
      >
        <Search className="size-4" /> Browse All Spots
      </Button>
      <ImportPopover />
    </div>
  );
}
