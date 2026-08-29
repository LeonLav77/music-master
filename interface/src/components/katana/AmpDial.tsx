import { cn } from "@/lib/utils";
import { AMP_MODEL_OPTIONS, PANEL_AMP_MODELS, UNDOCUMENTED_AMP_MODELS } from "@/lib/katana/schema";
import { useDragValue } from "./use-drag-value";

type Props = {
  value: number;
  onChange: (i: number) => void;
  size?: number;
};

/** Recessed glass orbital selector — amp model is set-and-forget, so it stays quiet. */
export function AmpDial({ value, onChange, size = 150 }: Props) {
  const n = AMP_MODEL_OPTIONS.length;
  // Dragging walks the option list; the amp's numbering may have gaps, so
  // step by position and translate back to the real value.
  const index = Math.max(0, AMP_MODEL_OPTIONS.findIndex((o) => o.value === value));
  const drag = useDragValue({
    value: index,
    min: 0,
    max: n - 1,
    holdKey: "amp_type",
    onChange: (i) => onChange(AMP_MODEL_OPTIONS[i]?.value ?? value),
    travel: 260,
  });
  const name = AMP_MODEL_OPTIONS.find((o) => o.value === value)?.label ?? "—";
  const isPanel = PANEL_AMP_MODELS.includes(value);
  const isUndoc = UNDOCUMENTED_AMP_MODELS.includes(value);

  const R = 38;
  const pointer = (index / n) * 360;

  const orbitLabels = [
    { label: "clean", angle: -90 },
    { label: "crunch", angle: 0 },
    { label: "lead", angle: 90 },
    { label: "metal", angle: 180 },
  ];

  return (
    <div className="flex select-none flex-col items-center gap-2">
      <div
        role="slider"
        aria-label="Amp model"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={n - 1}
        aria-valuetext={name}
        tabIndex={0}
        style={{ width: size, height: size }}
        className="relative touch-none cursor-grab rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing"
        {...drag}
      >
        {/* subtle outer orbital ring */}
        <div
          className="pointer-events-none absolute inset-0 rounded-full border border-white/[0.04] bg-gradient-to-br from-white/[0.05] to-transparent"
          aria-hidden
        />

        {/* orbital category labels */}
        {orbitLabels.map((o) => {
          const a = o.angle * (Math.PI / 180);
          const x = 50 + (R + 11) * Math.cos(a);
          const y = 50 + (R + 11) * Math.sin(a);
          return (
            <span
              key={o.label}
              className="pointer-events-none absolute translate-x-[-50%] translate-y-[-50%] font-mono text-[0.5rem] uppercase tracking-[0.18em] text-muted-foreground/40"
              style={{ left: `${x}%`, top: `${y}%` }}
            >
              {o.label}
            </span>
          );
        })}

        <svg viewBox="0 0 100 100" className="h-full w-full">
          {/* faint tick ring */}
          {AMP_MODEL_OPTIONS.map((m, i) => {
            const a = ((i / n) * 360 - 90) * (Math.PI / 180);
            const inner = PANEL_AMP_MODELS.includes(m.value) ? R - 5 : R - 3;
            const x1 = 50 + inner * Math.cos(a);
            const y1 = 50 + inner * Math.sin(a);
            const x2 = 50 + R * Math.cos(a);
            const y2 = 50 + R * Math.sin(a);
            const active = m.value === value;
            return (
              <line
                key={m.value}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                strokeWidth={active ? 2.2 : 1}
                strokeLinecap="round"
                className={cn(
                  active
                    ? "stroke-signal-cyan"
                    : UNDOCUMENTED_AMP_MODELS.includes(i)
                      ? "stroke-muted-foreground/25"
                      : "stroke-steel/30",
                )}
                onPointerDown={(ev) => {
                  ev.stopPropagation();
                  onChange(i);
                }}
              />
            );
          })}

          {/* selection indicator arc */}
          <g transform={`rotate(${pointer} 50 50)`}>
            <line x1="50" y1="16" x2="50" y2="25" strokeWidth={2} className="stroke-signal-cyan" />
          </g>

          {/* glass center disc */}
          <circle
            cx="50"
            cy="50"
            r="28"
            className="fill-panel/60 stroke-hairline/60"
            strokeWidth={1}
            style={{ backdropFilter: "blur(4px)" }}
          />
        </svg>

        {/* center readout */}
        <div className="pointer-events-none absolute inset-0 grid place-content-center px-6 text-center">
          <span className="font-mono text-[0.55rem] uppercase tracking-[0.16em] text-muted-foreground/70">
            {isUndoc ? "mkII only" : isPanel ? "panel" : "midi only"} · {value}
          </span>
          <span className="mt-0.5 font-display text-[0.72rem] leading-tight tracking-wide text-foreground/90">
            {name}
          </span>
        </div>
      </div>

      {/* compact arrow controls */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onChange((value - 1 + n) % n)}
          aria-label="Previous amp type"
          // Touch target, not a caret: this panel is finger-driven.
          className="grid h-8 w-8 place-items-center rounded-[3px] border border-hairline/60 bg-panel/60 font-mono text-[0.8rem] text-muted-foreground/70 hover:text-foreground active:bg-panel"
        >
          ‹
        </button>
        <span className="px-1 font-mono text-[0.55rem] uppercase tracking-[0.16em] text-muted-foreground/50">
          amp
        </span>
        <button
          type="button"
          onClick={() => onChange((value + 1) % n)}
          aria-label="Next amp type"
          // Touch target, not a caret: this panel is finger-driven.
          className="grid h-8 w-8 place-items-center rounded-[3px] border border-hairline/60 bg-panel/60 font-mono text-[0.8rem] text-muted-foreground/70 hover:text-foreground active:bg-panel"
        >
          ›
        </button>
      </div>
    </div>
  );
}
