import { cn } from "@/lib/utils";
import { EQ_BANDS } from "@/lib/katana/schema";
import { useDragValue } from "./use-drag-value";

type Vals = Record<string, number>;

export function EqCurve({ values, on }: { values: Vals; on: boolean }) {
  const pts = EQ_BANDS.map((b, i) => {
    const v = values[b.key] ?? 0;
    const x = (i / (EQ_BANDS.length - 1)) * 100;
    const y = 50 - (v / 24) * 42;
    return [x, y] as const;
  });
  const d = pts
    .map(([x, y], i) => (i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`))
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full">
      <line x1="0" y1="50" x2="100" y2="50" className="stroke-hairline" strokeWidth={0.6} />
      <path
        d={`${d} L 100 100 L 0 100 Z`}
        className={on ? "fill-steel/10" : "fill-muted/10"}
        stroke="none"
      />
      <path
        d={d}
        fill="none"
        strokeWidth={1.6}
        vectorEffect="non-scaling-stroke"
        className={on ? "stroke-steel" : "stroke-muted-foreground/50"}
      />
    </svg>
  );
}

function Fader({
  label,
  value,
  onChange,
  paramKey,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  paramKey?: string;
}) {
  const drag = useDragValue({
    value,
    min: -24,
    max: 24,
    ...(paramKey ? { holdKey: paramKey } : {}),
    onChange,
    travel: 200,
  });
  const pct = ((value + 24) / 48) * 100;
  return (
    <div className="flex min-w-0 flex-col items-center gap-1.5">
      <span className="font-mono text-[0.6rem] tabular-nums text-steel">
        {value > 0 ? `+${value}` : value}
      </span>
      <div
        role="slider"
        aria-label={`${label} Hz`}
        aria-valuenow={value}
        aria-valuemin={-24}
        aria-valuemax={24}
        tabIndex={0}
        className="relative h-40 w-8 touch-none cursor-ns-resize rounded-[3px] border border-hairline bg-panel outline-none focus-visible:ring-2 focus-visible:ring-ring"
        {...drag}
      >
        <div className="absolute inset-x-1 top-1/2 h-px bg-hairline" />
        <div
          className="absolute inset-x-1 rounded-[2px] bg-steel/20"
          style={
            value >= 0
              ? { bottom: "50%", height: `${(value / 48) * 100}%` }
              : { top: "50%", height: `${(-value / 48) * 100}%` }
          }
        />
        <div
          className="absolute inset-x-0.5 h-2.5 rounded-[2px] bg-steel shadow-glow-steel"
          style={{ bottom: `calc(${pct}% - 5px)` }}
        />
      </div>
      <span className="font-mono text-[0.58rem] uppercase text-muted-foreground">{label}</span>
    </div>
  );
}

export function EqWall({
  values,
  onChange,
  className,
}: {
  values: Vals;
  onChange: (key: string, v: number) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex gap-2 overflow-x-auto pb-1", className)}>
      {EQ_BANDS.map((b) => (
        <Fader
          key={b.key}
          label={b.label}
          value={values[b.key] ?? 0}
          paramKey={b.key}
          onChange={(v) => onChange(b.key, v)}
        />
      ))}
    </div>
  );
}
