import { cn } from "@/lib/utils";
import { FOOTSWITCHES } from "@/lib/katana/schema";

type Props = {
  isOn: (block: string | null) => boolean;
  onPress: (cc: number, block: string | null) => void;
};

export function FootswitchRow({ isOn, onPress }: Props) {
  return (
    <div className="grid grid-flow-col auto-cols-fr gap-1.5">
      {FOOTSWITCHES.map((fs) => {
        const on = isOn(fs.block);
        return (
          <button
            key={fs.cc}
            type="button"
            onClick={() => onPress(fs.cc, fs.block)}
            title={`${fs.label} — CC${fs.cc}`}
            className={cn(
              "rounded-[3px] border px-0.5 py-2 text-center transition-colors",
              on
                ? "border-ember/70 bg-ember/10 text-ember"
                : "border-hairline bg-panel text-muted-foreground hover:text-foreground",
            )}
          >
            {/* The CC number was eating the width the name needed; it is
                developer detail, so it moves to the tooltip. */}
            <span className="block font-display text-[0.55rem] uppercase leading-tight tracking-normal">
              {fs.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
