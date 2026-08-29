import { cn } from "@/lib/utils";

/** A slow amp operation is running.
 *
 *  Switching channel or loading a patch is several seconds of MIDI during
 *  which nothing visibly changes and then everything changes at once.
 *  Without this the surface just looks frozen. */
export function BusyBar({ label }: { label: string | null }) {
  return (
    <div
      aria-live="polite"
      className={cn(
        "pointer-events-none fixed inset-x-0 top-0 z-50 transition-opacity duration-150",
        label ? "opacity-100" : "opacity-0",
      )}
    >
      <div className="h-0.5 w-full overflow-hidden bg-ember/15">
        <div className="h-full w-1/3 animate-[busy-sweep_1.1s_ease-in-out_infinite] bg-ember" />
      </div>
      {label && (
        <div className="flex justify-center">
          <span className="rounded-b-[3px] border border-t-0 border-ember/40 bg-panel px-3 py-1 font-mono text-[0.58rem] uppercase tracking-[0.18em] text-ember">
            {label}
          </span>
        </div>
      )}
    </div>
  );
}
