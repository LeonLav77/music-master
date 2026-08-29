import { Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LedColor } from "@/lib/katana/schema";

type Props = {
  label: string;
  sub?: string;
  on: boolean;
  led?: LedColor;
  onToggle: () => void;
  onOpen: () => void;
  compact?: boolean;
};

const LED_CLASS: Record<LedColor, string> = {
  off: "bg-muted-foreground/25",
  green: "bg-led-green shadow-[0_0_14px_var(--led-green)]",
  red: "bg-led-red shadow-[0_0_14px_var(--led-red)]",
  yellow: "bg-led-yellow shadow-[0_0_14px_var(--led-yellow)]",
};

/** Big, stompable pedal tile — the whole face is the switch. */
export function StompTile({ label, sub, on, led = "off", onToggle, onOpen, compact }: Props) {
  const color = label === "Boost" ? "coral" : label === "Mod" ? "cyan" : label === "FX" ? "lime" : label === "Delay" ? "violet" : label === "Reverb" ? "cyan" : "coral";
  const activeClass = {
    coral: "border-signal-coral text-signal-coral shadow-[0_10px_24px_color-mix(in_oklab,var(--signal-coral)_28%,transparent)]",
    cyan: "border-signal-cyan text-signal-cyan shadow-[0_10px_24px_color-mix(in_oklab,var(--signal-cyan)_28%,transparent)]",
    lime: "border-signal-lime text-signal-lime shadow-[0_10px_24px_color-mix(in_oklab,var(--signal-lime)_25%,transparent)]",
    violet: "border-signal-violet text-signal-violet shadow-[0_10px_24px_color-mix(in_oklab,var(--signal-violet)_28%,transparent)]",
  }[color];
  return (
    <div
      className={cn(
        "group relative min-w-0 overflow-hidden border transition-all duration-150 [clip-path:polygon(7%_0,93%_0,100%_12%,96%_100%,4%_100%,0_12%)] active:translate-y-1 active:shadow-none",
        on
          ? activeClass
          : "border-hairline bg-[linear-gradient(145deg,var(--panel-raised),var(--panel)_55%,var(--metal-dark))] shadow-[0_9px_0_var(--metal-dark),0_14px_20px_oklch(0_0_0/45%)] hover:border-steel/50",
      )}
    >
      {/* metal sheen */}
      <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--foreground)_35%,transparent),transparent)]" />
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={on}
        className={cn(
          "flex h-full w-full flex-col items-start justify-between gap-1 text-left outline-none before:absolute before:inset-x-[8%] before:top-2 before:h-px before:bg-metal-light/30",
          compact ? "px-3 py-2.5" : "px-3.5 py-3",
        )}
      >
        <span className="flex w-full items-center justify-between gap-2">
          <span
            className={cn(
              "min-w-0 truncate font-display uppercase leading-none tracking-[0.08em]",
              compact ? "text-base" : "text-lg xl:text-xl",

              on ? "text-current" : "text-foreground/85",
            )}
          >
            {label}
          </span>
          <span className="relative flex h-4 w-4 shrink-0 items-center justify-center">
            <span
              className={cn(
                "h-3 w-3 rounded-full transition-all",
                LED_CLASS[led],
                on && led !== "off" && "signal-breathe",
              )}
            />
          </span>
        </span>
        <span
          className={cn(
            "block w-full truncate font-mono text-[0.68rem] tracking-wide",
            on ? "text-current/80" : "text-muted-foreground",
          )}
        >
          {sub ?? (on ? "engaged" : "bypassed")}
        </span>
        <span
          className={cn(
            "mt-1 h-[3px] w-full rounded-full transition-all",
            on ? "bg-current shadow-[0_0_14px_currentColor]" : "bg-track",
          )}
        />
      </button>
      <button
        type="button"
        onClick={onOpen}
        aria-label={`${label} settings`}
        className="absolute bottom-1.5 right-1.5 rounded-[3px] border border-hairline bg-background/70 p-1.5 text-muted-foreground backdrop-blur hover:border-steel/60 hover:text-steel"
      >
        <Settings2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
