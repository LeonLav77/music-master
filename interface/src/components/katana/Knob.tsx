import { cn } from "@/lib/utils";
import { useDragValue } from "./use-drag-value";

type Props = {
  label: string;
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  size?: "sm" | "md" | "lg";
  accent?: "steel" | "ember";
  disabled?: boolean;
  unknown?: boolean;
  onChange?: (v: number) => void;
  /** Parameter key, so the store can hold it while dragging. */
  paramKey?: string;
};

// Fixed px sized these for the 9" panel; on a 13"+ screen the same knob is
// needlessly small. clamp() grows it with the viewport and stops at a size
// that still fits six across the amp plate.
const SIZES: Record<"sm" | "md" | "lg", string> = {
  sm: "clamp(60px, 5.6vw, 104px)",
  md: "clamp(96px, 7.4vw, 136px)",
  lg: "clamp(128px, 9vw, 168px)",
};

export function Knob({
  label,
  value,
  min = 0,
  max = 100,
  unit,
  size = "md",
  accent = "steel",
  disabled,
  unknown,
  onChange,
  paramKey,
}: Props) {
  const px = SIZES[size];
  const pct = max === min ? 0 : (value - min) / (max - min);
  const START = -135;
  const SWEEP = 270;
  const angle = START + pct * SWEEP;

  const drag = useDragValue({
    value,
    min,
    max,
    ...(paramKey ? { holdKey: paramKey } : {}),
    onChange: (v) => onChange?.(v),
    travel: size === "lg" ? 260 : 200,
  });

  const R = 44;
  const arc = (from: number, to: number) => {
    const rad = (a: number) => ((a - 90) * Math.PI) / 180;
    const x1 = 50 + R * Math.cos(rad(from));
    const y1 = 50 + R * Math.sin(rad(from));
    const x2 = 50 + R * Math.cos(rad(to));
    const y2 = 50 + R * Math.sin(rad(to));
    return `M ${x1} ${y1} A ${R} ${R} 0 ${to - from > 180 ? 1 : 0} 1 ${x2} ${y2}`;
  };

  const interactive = !disabled && !unknown && !!onChange;

  return (
    <div className="flex min-w-0 select-none flex-col items-center gap-1.5">
      <div
        role={interactive ? "slider" : undefined}
        aria-label={label}
        aria-valuenow={unknown ? undefined : value}
        aria-valuemin={min}
        aria-valuemax={max}
        tabIndex={interactive ? 0 : -1}
        style={{ width: px, maxWidth: "100%", height: "auto", aspectRatio: "1 / 1" }}
        className={cn(
          "relative touch-none outline-none [filter:drop-shadow(0_8px_7px_oklch(0_0_0/55%))]",
          interactive ? "cursor-ns-resize" : "cursor-default",
          "focus-visible:ring-2 focus-visible:ring-ring",
          disabled && "opacity-50",
        )}
        {...(interactive ? drag : {})}
      >
        <svg viewBox="0 0 100 100" className="h-full w-full overflow-visible">
          <defs>
            <radialGradient id={`cap-${label}`} cx="32%" cy="25%">
              <stop offset="0" stopColor="var(--metal-light)" />
              <stop offset="0.28" stopColor="var(--panel-raised)" />
              <stop offset="0.72" stopColor="var(--cap)" />
              <stop offset="1" stopColor="var(--metal-dark)" />
            </radialGradient>
          </defs>
          <path
            d={arc(START, START + SWEEP)}
            className="stroke-track"
            fill="none"
            strokeWidth={7}
            strokeLinecap="round"
          />
          {!unknown && (
            <path
              d={arc(START, angle + 0.01)}
              fill="none"
              strokeWidth={7}
              strokeLinecap="round"
              className={accent === "ember" ? "stroke-ember" : "stroke-steel"}
            />
          )}
          {/* skirt / body sitting on the plate */}
          <ellipse cx="50" cy="62" rx="36" ry="31" className="fill-metal-dark" opacity="0.9" />
          <ellipse cx="50" cy="58" rx="34" ry="30" fill={`url(#cap-${label})`} />
          <ellipse cx="50" cy="48" rx="31" ry="30" className="fill-metal-dark" />
          <circle cx="50" cy="48" r="30" fill={`url(#cap-${label})`} className="stroke-metal-light/30" strokeWidth={1.5} />
          {/* gloss highlight */}
          <ellipse cx="41" cy="33" rx="15" ry="8" fill="oklch(1 0 0 / 14%)" transform="rotate(-22 41 33)" />
          {Array.from({ length: 24 }, (_, i) => (
            <line key={i} x1="50" y1="17" x2="50" y2="22" transform={`rotate(${i * 15} 50 48)`} className="stroke-metal-light/30" strokeWidth="1.2" />
          ))}
          <g transform={`rotate(${angle} 50 48)`}>
            <line
              x1="50"
              y1="21"
              x2="50"
              y2="41"
              strokeWidth={4.5}
              strokeLinecap="round"
              stroke="oklch(0 0 0 / 60%)"
              transform="translate(0 1.5)"
            />
            <line
              x1="50"
              y1="21"
              x2="50"
              y2="41"
              strokeWidth={4}
              strokeLinecap="round"
              className={
                unknown ? "stroke-muted-foreground" : accent === "ember" ? "stroke-ember" : "stroke-steel"
              }
            />
          </g>

        </svg>
        <span
          className={cn(
            "pointer-events-none absolute inset-0 grid place-items-center font-mono tabular-nums",
            unknown ? "text-muted-foreground" : "text-foreground",
            size === "lg" && "text-lg xl:text-xl",
            size === "md" && "text-sm xl:text-base",
            size === "sm" && "text-[0.7rem] xl:text-sm",
          )}
        >
          {unknown ? "––" : `${Math.round(value)}${unit ?? ""}`}
        </span>
      </div>
      <span className={cn("font-bold uppercase text-foreground/75 [text-shadow:0_1px_0_oklch(1_0_0/18%)]", size === "sm" ? "text-[0.56rem] tracking-[0.12em] xl:text-[0.68rem]" : "text-[0.68rem] tracking-[0.18em] xl:text-[0.78rem]")}>
        {label}
      </span>
    </div>
  );
}
