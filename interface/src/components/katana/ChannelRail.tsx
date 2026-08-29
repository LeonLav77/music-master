import { useState } from "react";
import { cn } from "@/lib/utils";
import { useKatana } from "@/lib/katana/store";
import { CHANNELS, type ChannelId } from "@/lib/katana/schema";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

type Props = {
  current: ChannelId;
  names: Record<ChannelId, string>;
  onSelect: (id: ChannelId) => void;
  onSave: (id: ChannelId) => void;
  variant?: "rail" | "grid";
};

export function ChannelRail({
  current,
  names,
  onSelect,
  onSave,
  variant = "rail",
}: Props) {
  const { busy } = useKatana();
  const [pending, setPending] = useState<ChannelId | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;

  const holdStart = (id: ChannelId) => {
    timer = setTimeout(() => setPending(id), 650);
  };
  const holdEnd = () => {
    if (timer) clearTimeout(timer);
  };

  return (
    <>
      <div
        className={cn(
          variant === "rail"
            ? "grid grid-cols-3 gap-1.5 sm:grid-flow-col sm:auto-cols-fr sm:grid-cols-none"
            : "grid grid-cols-3 gap-2",
        )}
      >
        {CHANNELS.map((c) => {
          const active = c.id === current;
          const isPanel = c.id === "panel";
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onSelect(c.id)}
              onPointerDown={() => holdStart(c.id)}
              onPointerUp={holdEnd}
              onPointerLeave={holdEnd}
              aria-pressed={active}
              // Switching takes a few seconds of MIDI; queueing a second
              // one on top just makes the amp thrash.
              disabled={busy !== null}
              className={cn(
                "min-w-0 rounded-[4px] border px-2 py-2 text-left transition-colors disabled:opacity-50",
                active
                  ? "border-ember bg-ember/15 shadow-glow-ember"
                  : "border-hairline bg-panel hover:border-steel/40",
                isPanel && !active && "border-steel/30",
              )}
            >
              <span
                className={cn(
                  "block font-mono text-[0.58rem] uppercase tracking-[0.2em]",
                  active ? "text-ember" : "text-muted-foreground",
                )}
              >
                {isPanel ? "panel" : `${c.bank}${c.id.slice(1)}`}
              </span>
              <span className="mt-0.5 block truncate font-display text-[0.8rem] uppercase tracking-[0.08em] text-foreground">
                {names[c.id]}
              </span>
            </button>
          );
        })}
      </div>

      <AlertDialog
        open={pending !== null}
        onOpenChange={(o) => !o && setPending(null)}
      >
        <AlertDialogContent className="border-hairline bg-panel">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display uppercase tracking-[0.12em]">
              Overwrite {pending ? names[pending] : ""}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This writes the live panel sound into the stored slot. The sound
              currently saved there is lost permanently.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-ember text-ember-foreground hover:bg-ember/90"
              onClick={() => {
                if (pending) onSave(pending);
                setPending(null);
              }}
            >
              Overwrite
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
