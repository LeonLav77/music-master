import { useCallback, useRef, useState } from "react";
import { SlidersHorizontal, RotateCcw, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { EQ_BANDS } from "@/lib/katana/schema";
import { useKatana } from "@/lib/katana/store";

type Vals = Record<string, number>;

const N = EQ_BANDS.length;
const RANGE = 24;

/** Read-only mini curve used in collapsed strips. */
export function EqCurve({ values, on }: { values: Vals; on: boolean }) {
  const d = EQ_BANDS.map((b, i) => {
    const v = values[b.key] ?? 0;
    const x = (i / (N - 1)) * 100;
    const y = 50 - (v / RANGE) * 42;
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full">
      <line x1="0" y1="50" x2="100" y2="50" className="stroke-hairline" strokeWidth={0.6} />
      <path d={`${d} L 100 100 L 0 100 Z`} className={on ? "fill-steel/10" : "fill-muted/10"} />
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

/**
 * Draw-anywhere graphic EQ: drag across the pad and the band values follow
 * the finger, the numbers are derived instead of typed in.
 */
export function EqPad({
  values,
  on,
  onChange,
  className,
}: {
  values: Vals;
  on: boolean;
  onChange: (key: string, v: number) => void;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const lastIdx = useRef<number | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const { hold } = useKatana();

  const apply = useCallback(
    (clientX: number, clientY: number) => {
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const fx = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
      const fy = Math.min(1, Math.max(0, (clientY - r.top) / r.height));
      const idx = Math.round(fx * (N - 1));
      const val = Math.round((0.5 - fy) * 2 * RANGE);
      const clamped = Math.min(RANGE, Math.max(-RANGE, val));
      const prev = lastIdx.current;
      if (prev !== null && Math.abs(idx - prev) > 1) {
        // fill the gap when the finger moves fast
        const from = values[EQ_BANDS[prev]!.key] ?? 0;
        const step = idx > prev ? 1 : -1;
        for (let i = prev + step; i !== idx; i += step) {
          const t = (i - prev) / (idx - prev);
          onChange(EQ_BANDS[i]!.key, Math.round(from + (clamped - from) * t));
        }
      }
      lastIdx.current = idx;
      setHover(idx);
      onChange(EQ_BANDS[idx]!.key, clamped);
    },
    [onChange, values],
  );

  const pts = EQ_BANDS.map((b, i) => {
    const v = values[b.key] ?? 0;
    return {
      key: b.key,
      label: b.label,
      v,
      x: (i / (N - 1)) * 100,
      y: 50 - (v / RANGE) * 50,
    };
  });
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <div className={cn("flex min-h-0 flex-col gap-1", className)}>
      <div
        ref={ref}
        role="application"
        aria-label="Graphic EQ curve — drag to shape"
        className={cn(
          "relative min-h-0 flex-1 touch-none cursor-crosshair overflow-hidden rounded-[4px] border bg-panel",
          dragging ? "border-ember/60" : "border-hairline",
        )}
        onPointerDown={(e) => {
          (e.target as Element).setPointerCapture?.(e.pointerId);
          lastIdx.current = null;
          setDragging(true);
          // Drawing sweeps across bands, so hold the whole row until the
          // gesture ends rather than one band at a time.
          EQ_BANDS.forEach((b) => hold(b.key, true));
          apply(e.clientX, e.clientY);
        }}
        onPointerMove={(e) => {
          if (!dragging) return;
          apply(e.clientX, e.clientY);
        }}
        onPointerUp={(e) => {
          (e.target as Element).releasePointerCapture?.(e.pointerId);
          setDragging(false);
          lastIdx.current = null;
          EQ_BANDS.forEach((b) => hold(b.key, false));
        }}
        onPointerLeave={() => !dragging && setHover(null)}
      >
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
          <line x1="0" y1="50" x2="100" y2="50" className="stroke-hairline" strokeWidth={0.5} />
          <line x1="0" y1="25" x2="100" y2="25" className="stroke-hairline/60" strokeWidth={0.3} />
          <line x1="0" y1="75" x2="100" y2="75" className="stroke-hairline/60" strokeWidth={0.3} />
          {pts.map((p) => (
            <line
              key={p.key}
              x1={p.x}
              y1="0"
              x2={p.x}
              y2="100"
              className="stroke-hairline/50"
              strokeWidth={0.3}
            />
          ))}
          <path
            d={`${d} L 100 50 L 0 50 Z`}
            className={on ? "fill-ember/15" : "fill-muted/10"}
          />
          <path
            d={d}
            fill="none"
            strokeWidth={2.5}
            vectorEffect="non-scaling-stroke"
            className={on ? "stroke-ember" : "stroke-muted-foreground/50"}
          />
        </svg>
        {pts.map((p, i) => (
          <span
            key={p.key}
            className={cn(
              "pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 rounded-full transition-all",
              on ? "bg-ember" : "bg-muted-foreground",
              hover === i ? "h-3 w-3 shadow-glow-ember" : "h-2 w-2",
            )}
            style={{ left: `${p.x}%`, top: `${p.y}%` }}
          />
        ))}
        {hover !== null && (
          <span
            className="pointer-events-none absolute -translate-x-1/2 rounded-[3px] border border-ember/50 bg-background px-1.5 py-0.5 font-mono text-[0.6rem] tabular-nums text-ember"
            style={{
              left: `${Math.min(92, Math.max(8, pts[hover]!.x))}%`,
              top: `calc(${pts[hover]!.y}% - 22px)`,
            }}
          >
            {pts[hover]!.label} {pts[hover]!.v > 0 ? `+${pts[hover]!.v}` : pts[hover]!.v}
          </span>
        )}
      </div>
      <div className="flex shrink-0 justify-between font-mono text-[0.52rem] uppercase tracking-[0.1em] text-muted-foreground">
        {pts.map((p) => (
          <span key={p.key} className="tabular-nums">
            {p.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/** EQ is physically hidden until its small rack hatch is deliberately opened. */
export function EqDock({
  values,
  on,
  onToggle,
  onChange,
  onFlat,
  onSetup,
  height = 190,
}: {
  values: Vals;
  on: boolean;
  onToggle: () => void;
  onChange: (key: string, v: number) => void;
  onFlat: () => void;
  onSetup?: () => void;
  height?: number;
}) {
  const [openPad, setOpenPad] = useState(false);
  return (
    <section className="shrink-0">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setOpenPad((o) => !o)}
          aria-expanded={openPad}
          className={cn("flex items-center gap-2 border px-3 py-1.5 font-mono text-[0.58rem] uppercase tracking-[0.18em] shadow-[0_4px_0_var(--metal-dark)]", openPad ? "border-signal-cyan bg-panel-raised text-signal-cyan" : "border-hairline bg-panel text-muted-foreground")}
        >
          {openPad ? <X className="h-3.5 w-3.5" /> : <SlidersHorizontal className="h-3.5 w-3.5" />}
          {openPad ? "close tone hatch" : "tone hatch"}
        </button>
      </div>
      {openPad && (
        // Fixed, not absolute: the dock's wrapper is itself `fixed` and only
        // as wide as the button, so `inset-x-3` used to resolve against a
        // ~140px box and crush the pad into an unusable strip.
        <div className="fixed inset-x-3 bottom-3 z-40 mx-auto max-w-[900px] border border-signal-cyan/60 bg-background/95 p-3 shadow-[0_-16px_50px_oklch(0_0_0/75%)] backdrop-blur-xl">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="font-display text-sm font-bold uppercase text-signal-cyan">Draw tone contour</span>
            <span className="font-mono text-[0.52rem] uppercase text-muted-foreground">drag anywhere</span>
            <span className="flex-1" />
            <button
              type="button"
              onClick={onFlat}
              className="flex items-center gap-1 border border-hairline px-2 py-1.5 font-mono text-[0.55rem] uppercase tracking-[0.16em] text-muted-foreground hover:text-steel"
            >
              <RotateCcw className="h-3 w-3" />
              flat
            </button>
            {onSetup && (
              <button
                type="button"
                onClick={onSetup}
                className="border border-hairline px-2 py-1.5 font-mono text-[0.55rem] uppercase tracking-[0.16em] text-muted-foreground hover:text-steel"
              >
                faders
              </button>
            )}
            <button
              type="button"
              onClick={onToggle}
              aria-pressed={on}
              className={cn(
                "border px-2.5 py-1.5 font-mono text-[0.58rem] uppercase tracking-[0.18em]",
                on ? "border-ember/70 bg-ember/10 text-ember" : "border-hairline text-muted-foreground",
              )}
            >
              {on ? "on" : "off"}
            </button>
            <button
              type="button"
              onClick={() => setOpenPad(false)}
              aria-label="Close EQ"
              className="border border-hairline p-1.5 text-muted-foreground hover:text-steel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div style={{ height }}>
            <EqPad values={values} on={on} onChange={onChange} className="h-full" />
          </div>
        </div>
      )}
    </section>
  );
}
