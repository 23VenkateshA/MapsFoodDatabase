export function CountPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex min-w-[22px] h-5 items-center justify-center rounded-full bg-secondary px-2 text-xs font-semibold text-muted-foreground tabular-nums">
      {children}
    </span>
  );
}

export function SectionHeader({ title, count }: { title: string; count: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 my-2">
      <h3 className="text-base font-semibold m-0">{title}</h3>
      <CountPill>{count}</CountPill>
    </div>
  );
}
