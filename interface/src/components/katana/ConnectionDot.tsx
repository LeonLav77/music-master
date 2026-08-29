import { cn } from "@/lib/utils";
import type { ConnectionState } from "@/lib/katana/transport";

const LABELS: Record<ConnectionState, string> = {
  open: "live",
  connecting: "connecting",
  closed: "offline",
};

/** Whether the amp is actually reachable.
 *
 *  Without this a disconnected surface looks identical to a working one -
 *  you would drag controls into the void and never know. */
export function ConnectionDot({ state }: { state: ConnectionState }) {
  return (
    <span className="flex shrink-0 items-center gap-1.5" title={`Amp ${LABELS[state]}`}>
      <span
        aria-hidden
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          state === "open" && "bg-steel shadow-glow-steel",
          state === "connecting" && "animate-pulse bg-foreground/40",
          state === "closed" && "bg-ember shadow-glow-ember",
        )}
      />
      <span className="engrave font-mono text-[0.52rem] uppercase tracking-[0.16em]">
        {LABELS[state]}
      </span>
    </span>
  );
}
