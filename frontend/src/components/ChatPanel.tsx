"use client";

import { AlertCircle, MessageSquare, Search } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAppState } from "@/lib/app-state";
import { SectionHeader } from "./CountPill";
import { SpotCard } from "./SpotCard";

const EXAMPLE_PROMPTS = [
  "Asian happy hour in East Village",
  "Group dinner for 6",
  "Best pizza in Alphabet City",
];

export function ChatPanel() {
  const { messages, lastSpots, lastSummary, lastFilters, chatLoading, chatError, sendQuery } = useAppState();
  const [input, setInput] = useState("");

  function submit(query: string) {
    const trimmed = query.trim();
    if (!trimmed || chatLoading) return;
    setInput("");
    void sendQuery(trimmed);
  }

  return (
    <div>
      <div className="rounded-lg border border-border bg-card/40 h-[380px] flex flex-col">
        <ScrollArea className="flex-1 p-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-3 text-center text-muted-foreground py-8">
              <MessageSquare className="size-8" />
              <p className="text-sm max-w-xs">Ask about a vibe, neighborhood, or occasion — try one below.</p>
              <div className="flex flex-wrap justify-center gap-2 mt-1">
                {EXAMPLE_PROMPTS.map((p) => (
                  <Button key={p} size="sm" variant="outline" onClick={() => submit(p)}>
                    {p}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                  <div
                    className={`inline-block rounded-lg px-3 py-2 text-sm max-w-[85%] ${
                      m.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary"
                    }`}
                  >
                    {m.content}
                  </div>
                </div>
              ))}
              {chatLoading && <p className="text-sm text-muted-foreground">Finding spots…</p>}
            </div>
          )}
        </ScrollArea>
      </div>

      {lastFilters.length > 0 && (
        <div className="mt-3">
          <p className="text-sm text-muted-foreground mb-1.5">Quick filters:</p>
          <div className="flex flex-wrap gap-2">
            {lastFilters.map((f) => (
              <Button key={f} size="sm" variant="outline" onClick={() => submit(f)}>
                {f}
              </Button>
            ))}
          </div>
        </div>
      )}

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Asian happy hour in East Village for 6 people"
          disabled={chatLoading}
        />
        <Button type="submit" disabled={chatLoading || !input.trim()}>
          Send
        </Button>
      </form>

      {chatError && (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-destructive">
          <AlertCircle className="size-4" /> {chatError}
        </p>
      )}

      <div className="mt-6">
        <SectionHeader title="Recommendations" count={lastSpots.length} />
        {lastSummary && <p className="mb-3 text-sm rounded-lg bg-primary/10 text-primary px-3 py-2">{lastSummary}</p>}
        {lastSpots.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 text-center text-muted-foreground py-10">
            <Search className="size-8" />
            <p className="text-sm">Ask a question above to get recommendations.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {lastSpots.map((spot) => (
              <SpotCard key={spot.id} spot={spot} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
