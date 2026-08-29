import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { useKatana } from "@/lib/katana/store";

type Props = {
  value: number;
  min: number;
  max: number;
  on: boolean;
  onChange: (v: number) => void;
  onSweep: () => void;
  onSetup?: () => void;
  onToggle?: () => void;
  orientation?: "vertical" | "horizontal";
  className?: string;
};

/** The one control meant to be swept: the whole slab is the pedal. */
export function Treadle({
  value,
  min,
  max,
  on,
  onChange,
  onSweep,
  onSetup,
  onToggle,
  orientation = "vertical",
  className,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const { hold } = useKatana();
  const vertical = orientation === "vertical";

  const apply = useCallback(
    (x: number, y: number) => {
      const r = ref.current?.getBoundingClientRect();
      if (!r) return;
      const f = vertical ? 1 - (y - r.top) / r.height : (x - r.left) / r.width;
      onChange(Math.round(Math.min(100, Math.max(0, f * 100))));
    },
    [onChange, vertical],
  );

  const tilt = vertical ? 42 - value * 0.6 : 26 - value * 0.42;
  return (
    <div className={cn("flex min-h-0 min-w-0 flex-col gap-2 [perspective:520px] [perspective-origin:50%_85%]", className)}>

      <div className="flex shrink-0 items-baseline justify-between gap-2">
        <span className="font-display text-sm uppercase tracking-[0.2em] text-foreground xl:text-lg">Wah</span>
        <span className="font-mono text-[0.6rem] tabular-nums text-muted-foreground">
          {min}–{max}
        </span>
      </div>

      <div
        ref={ref}
        role="slider"
        aria-label="Wah treadle position"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        tabIndex={0}
        onKeyDown={(e) => {
          const d = e.key === "ArrowUp" || e.key === "ArrowRight" ? 2 : e.key === "ArrowDown" || e.key === "ArrowLeft" ? -2 : 0;
          if (!d) return;
          e.preventDefault();
          onChange(Math.min(100, Math.max(0, value + d)));
        }}
        onPointerDown={(e) => {
          if (!on) {
            // Dragging a switched-off pedal does nothing on the amp, so
            // the slab turns it on instead of pretending to work.
            onToggle?.();
            return;
          }
          (e.target as Element).setPointerCapture?.(e.pointerId);
          setDragging(true);
          hold("wah_position", true);
          apply(e.clientX, e.clientY);
        }}
        onPointerMove={(e) => on && dragging && apply(e.clientX, e.clientY)}
        onPointerUp={(e) => {
          (e.target as Element).releasePointerCapture?.(e.pointerId);
          setDragging(false);
          hold("wah_position", false);
        }}
        className={cn(
          // The children are absolutely positioned, so the slab needs a real
          // height of its own. Inside a sheet the parent has no height and
          // `flex-1` collapsed to ~0, stacking the readout, the "wah is off"
          // banner and the treadle graphic on a single line.
          "relative min-h-0 flex-1 touch-none select-none outline-none",
          vertical ? "min-h-[180px] xl:min-h-[300px]" : "min-h-[92px] xl:min-h-[130px]",
          on ? (vertical ? "cursor-ns-resize" : "cursor-ew-resize") : "cursor-pointer",
          dragging && "scale-[0.99]",
        )}
      >
        {/* cast-iron rocker housing */}
        <span className="pointer-events-none absolute inset-x-[4%] bottom-0 h-[26%] rounded-b-[6px] bg-[linear-gradient(180deg,var(--panel-raised),var(--metal-dark))] [clip-path:polygon(6%_0,94%_0,100%_100%,0_100%)] shadow-[0_14px_24px_oklch(0_0_0/75%)]" />
        {/* side rails */}
        <span className="pointer-events-none absolute inset-y-[6%] left-[2%] w-[5%] rounded bg-[linear-gradient(90deg,var(--metal-dark),var(--panel-raised))] shadow-[inset_-1px_0_0_oklch(1_0_0/12%)]" />
        <span className="pointer-events-none absolute inset-y-[6%] right-[2%] w-[5%] rounded bg-[linear-gradient(270deg,var(--metal-dark),var(--panel-raised))] shadow-[inset_1px_0_0_oklch(1_0_0/12%)]" />
        {/* glow spilling from under the treadle */}
        <span
          className={cn(
            "pointer-events-none absolute inset-x-[14%] bottom-[16%] h-[34%] blur-xl transition-opacity",
            on ? "bg-signal-lime/45" : "bg-signal-cyan/20",
          )}
        />
        {/* pivot bolt */}
        <span className="pointer-events-none absolute bottom-[11%] left-1/2 z-20 h-6 w-6 -translate-x-1/2 rounded-full border border-metal-light/50 bg-[radial-gradient(circle_at_34%_28%,var(--metal-light),var(--metal-dark)_70%)] shadow-[0_3px_6px_oklch(0_0_0/85%)] after:absolute after:inset-[38%] after:rounded-full after:bg-metal-dark" />

        <div
          className={cn(
            "pointer-events-none absolute inset-x-[9%] bottom-[10%] top-[3%] origin-bottom rounded-t-[5px] border-2 bg-[linear-gradient(160deg,oklch(0.78_0.012_245),oklch(0.5_0.01_248)_22%,oklch(0.3_0.008_252)_62%,var(--metal-dark))] shadow-[0_26px_34px_oklch(0_0_0/78%),inset_0_3px_0_oklch(1_0_0/55%),inset_0_-6px_14px_oklch(0_0_0/70%)] transition-transform duration-100 [clip-path:polygon(18%_0,82%_0,100%_7%,97%_100%,3%_100%,0_7%)] [transform-style:preserve-3d] after:absolute after:inset-x-[18%] after:-top-[6px] after:h-[7px] after:rounded-t-[4px] after:bg-[linear-gradient(180deg,oklch(0.85_0.01_245),oklch(0.42_0.01_250))] after:shadow-[0_-2px_6px_oklch(0_0_0/60%)]",
            on ? "border-signal-lime/80" : "border-signal-cyan/40",
          )}
          style={{ transform: vertical ? `rotateX(${tilt}deg)` : `rotateY(${-tilt}deg)` }}
        >
          {/* rubber tread ribs */}
          <span
            className="pointer-events-none absolute inset-x-[12%] top-[8%] bottom-[16%] rounded-sm opacity-90"
            style={{
              backgroundImage: `repeating-linear-gradient(${vertical ? "0deg" : "90deg"}, oklch(0.07 0 0) 0 4px, oklch(0.3 0.006 250) 4px 6px, oklch(0.12 0.004 250) 6px 11px)`,
            }}
          />
          {/* toe LED */}
          <span
            className={cn(
              "absolute left-1/2 top-[4%] h-2.5 w-2.5 -translate-x-1/2 rounded-full",
              on ? "bg-signal-lime shadow-[0_0_16px_var(--signal-lime)] signal-breathe" : "bg-signal-lime/25",
            )}
          />
          {/* heel bar */}
          <span
            className={cn(
              "absolute inset-x-[24%] bottom-[4%] h-1 rounded-full",
              on ? "bg-signal-cyan shadow-[0_0_16px_var(--signal-cyan)]" : "bg-signal-cyan/40",
            )}
          />
        </div>

        {[min, max].map((m, i) => (
          <div
            key={i}
            className="absolute border-dashed border-muted-foreground/60"
            style={
              vertical
                ? { left: 0, right: 0, bottom: `${m}%`, borderTopWidth: 1 }
                : { top: 0, bottom: 0, left: `${m}%`, borderLeftWidth: 1 }
            }
          />
        ))}
        <span
          className={cn(
            "pointer-events-none absolute inset-0 grid place-items-center font-display text-4xl font-black tabular-nums [text-shadow:0_4px_10px_oklch(0_0_0/80%)] xl:text-6xl",
            on ? "text-signal-lime" : "text-signal-cyan/60",
          )}
        >
          {Math.round(value)}
        </span>
        {/* Why the treadle is not responding. */}
        {!on && onToggle && (
          <span className="pointer-events-none absolute inset-x-0 bottom-0 bg-background/75 py-2 text-center font-mono text-[0.58rem] uppercase tracking-[0.18em] text-signal-lime">
            wah is off — tap to enable
          </span>
        )}
      </div>

      <div className="grid shrink-0 grid-cols-3 gap-1.5">
        {onToggle && (
          <button
            type="button"
            onClick={onToggle}
            aria-pressed={on}
            // Says what pressing it does, not what the state is - "WAH ON"
            // reads as a status badge and nobody presses it to turn off.
            className={cn(
              "flex items-center justify-center gap-1.5 border px-1 py-1.5 font-display text-[0.62rem] uppercase tracking-[0.16em] transition-colors xl:py-3 xl:text-[0.74rem]",
              on
                ? "border-signal-lime bg-signal-lime/20 text-signal-lime shadow-[0_0_10px_-2px_var(--signal-lime)] hover:bg-signal-lime/30"
                : "border-signal-lime/40 text-signal-lime/70 hover:bg-signal-lime/10",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                on ? "bg-signal-lime" : "border border-signal-lime/50",
              )}
            />
            {on ? "turn off" : "turn on"}
          </button>
        )}
        <button
          type="button"
          onClick={onSweep}
          className="border border-signal-cyan/50 px-1 py-1.5 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-signal-cyan hover:bg-signal-cyan/10 xl:py-3 xl:text-[0.68rem]"
        >
          sweep
        </button>
        {onSetup && (
          <button
            type="button"
            onClick={onSetup}
            className="border border-hairline px-1 py-1.5 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-muted-foreground hover:text-steel xl:py-3 xl:text-[0.68rem]"
          >
            setup
          </button>
        )}
      </div>
    </div>
  );
}
