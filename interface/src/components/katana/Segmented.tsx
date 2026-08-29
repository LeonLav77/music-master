import { cn } from "@/lib/utils";

import type { EnumOption } from "@/lib/katana/generated";

type Props = {
  label?: string;
  /** The amp's own numbering, which is sparse - never use the array index. */
  options: EnumOption[];
  value: number;
  onChange: (value: number) => void;
  columns?: number;
  size?: "sm" | "md";
};

/** Replaces every dropdown: a flat, always-visible pick row. */
export function Segmented({ label, options, value, onChange, columns, size = "md" }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <span className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground xl:text-[0.72rem]">
          {label}
        </span>
      )}
      {/* Auto-fit rather than one forced row: seven reverb names on a 390px
          phone were being squeezed to ~39px and clipped mid-word. */}
      <div
        className={cn("grid gap-1 xl:gap-2", !columns && "[grid-template-columns:repeat(auto-fit,minmax(84px,1fr))] xl:[grid-template-columns:repeat(auto-fit,minmax(130px,1fr))]")}
        style={columns ? { gridTemplateColumns: `repeat(${columns}, minmax(0,1fr))` } : undefined}
      >
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            aria-pressed={o.value === value}
            className={cn(
              "flex items-center justify-center rounded-[3px] border px-2 text-center font-semibold uppercase leading-tight tracking-wide transition-colors",
              size === "sm" ? "py-1.5 text-[0.6rem] xl:py-3 xl:text-[0.74rem]" : "py-2.5 text-[0.68rem] xl:py-4 xl:text-[0.82rem]",
              o.value === value
                ? "border-steel bg-steel/15 text-steel shadow-glow-steel"
                : "border-hairline bg-panel text-muted-foreground hover:border-steel/40 hover:text-foreground",
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
