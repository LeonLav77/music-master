import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { RefreshCw, FolderOpen } from "lucide-react";
import { useKatana } from "@/lib/katana/store";
import { transport } from "@/lib/katana/transport";
import { EQ_BANDS } from "@/lib/katana/schema";
import { AmpDial } from "./AmpDial";
import { ChannelRail } from "./ChannelRail";
import { EqDock } from "./EqPad";
import { Knob } from "./Knob";
import { StompTile } from "./StompTile";
import { Treadle } from "./Treadle";
import { BlockEditor, BLOCK_TITLES, type BlockId } from "./BlockEditor";
import { AMP_KNOBS, buildBlocks } from "./surface-shared";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { BusyBar } from "./BusyBar";
import { ConnectionDot } from "./ConnectionDot";

/** Layout dedicated to the phone: one thumb, stacked, no side-by-side columns. */
export function MobileSurface() {
  const k = useKatana();
  const [open, setOpen] = useState<BlockId | null>(null);
  const [channels, setChannels] = useState(false);
  const eqValues = Object.fromEntries(EQ_BANDS.map((b) => [b.key, k.num(b.key)]));
  const blocks = buildBlocks(k);

  return (
    <>
      <BusyBar label={k.busy} />
    <main className="min-h-screen w-full pb-6">
      <header className="sticky top-0 z-20 border-b border-hairline bg-background/95 px-3 py-2 backdrop-blur">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setChannels((c) => !c)}
            className="min-w-0 flex-1 text-left"
          >
            <span className="block truncate font-display text-base uppercase tracking-[0.18em] text-foreground">
              {k.channelNames[k.channel]}
            </span>
            <span className="block font-mono text-[0.55rem] uppercase tracking-[0.18em] text-muted-foreground">
              {channels ? "hide channels" : "tap to change channel"}
              {k.dirty && <span className="text-ember"> · edited</span>}
            </span>
          </button>
          <ConnectionDot state={k.connection} />
          <button
            type="button"
            onClick={k.resync}
            aria-label="Resync"
            className="rounded-[3px] border border-steel/50 p-2 text-steel"
          >
            <RefreshCw className={cn("h-4 w-4", k.syncing && "animate-spin")} />
          </button>
          <Link to="/patches" aria-label="Patches" className="rounded-[3px] border border-hairline p-2 text-muted-foreground">
            <FolderOpen className="h-4 w-4" />
          </Link>
        </div>
        {channels && (
          <div className="pt-2">
            <ChannelRail
              current={k.channel}
              names={k.channelNames}
              onSelect={(id) => {
                k.selectChannel(id);
                setChannels(false);
              }}
              onSave={k.saveToChannel}
              variant="grid"
            />
          </div>
        )}
      </header>

      <div className="flex flex-col gap-3 px-3 pt-3">
        {/* Amp */}
        <section className="amp-plate relative flex flex-col items-center gap-3 rounded-[6px] p-3">
          <AmpDial value={k.num("amp_type")} onChange={(i) => k.set("amp_type", i)} size={196} />
          <div className="grid w-full grid-cols-3 justify-items-center gap-y-3">
            {AMP_KNOBS.map((kn) => (
              <Knob
                key={kn.key}
                paramKey={kn.key}
                label={kn.label}
                value={k.num(kn.key)}
                accent={kn.accent}
                size="md"
                onChange={(v) => k.set(kn.key, v)}
              />
            ))}
          </div>
          <div className="flex w-full items-center gap-3">
            <button
              type="button"
              onClick={() => k.toggle("bright")}
              aria-pressed={k.bool("bright")}
              className={cn(
                "flex-1 rounded-[4px] border py-3 font-display text-sm uppercase tracking-[0.18em]",
                k.bool("bright")
                  ? "border-steel bg-steel/15 text-steel shadow-glow-steel"
                  : "border-hairline bg-panel text-muted-foreground",
              )}
            >
              bright
            </button>
            <Knob label="Knob Vol" value={k.num("knob_volume")} size="sm" disabled />
          </div>
        </section>

        {/* Pedals */}
        <section className="amp-grille grid grid-cols-2 gap-3 rounded-[6px] p-3">
          {blocks.map((b) => (
            <StompTile
              key={b.id}
              label={b.label}
              sub={b.sub}
              on={k.bool(b.sw)}
              led={b.led ? k.led(b.led) : "off"}
              onToggle={() => k.toggle(b.sw)}
              onOpen={() => setOpen(b.id)}
            />
          ))}
        </section>

        {/* Wah */}
        <section className="amp-tolex min-h-[220px] rounded-[6px] border border-metal-dark/60 p-3">
          <Treadle
            value={k.num("wah_position")}
            min={k.num("wah_pedal_min")}
            max={k.num("wah_pedal_max")}
            on={k.bool("pedal_switch")}
            orientation="horizontal"
            onChange={(v) => k.set("wah_position", v)}
            onToggle={() => k.setWah(!k.bool("pedal_switch"))}
            onSweep={() => transport.sweepWah(k.num("wah_pedal_min"), k.num("wah_pedal_max"), 900)}
            onSetup={() => setOpen("wah")}
          />
        </section>

        <div className="sticky bottom-3 z-30 ml-auto"><EqDock
          values={eqValues}
          on={k.bool("eq_switch")}
          onToggle={() => k.toggle("eq_switch")}
          onChange={(key, v) => k.set(key, v)}
          onFlat={() => EQ_BANDS.forEach((b) => k.set(b.key, 0))}
          onSetup={() => setOpen("eq")}
          height={200}
        /></div>

        <p className="font-mono text-[0.55rem] uppercase tracking-[0.16em] text-muted-foreground">
          amp never reports panel knob turns — resync to trust these values
        </p>
      </div>

      <Sheet open={open !== null} onOpenChange={(o) => !o && setOpen(null)}>
        <SheetContent side="bottom" className="max-h-[90vh] overflow-y-auto border-hairline bg-background">
          <SheetHeader className="px-4 pt-4 xl:px-10 xl:pt-8">
            <SheetTitle className="font-display text-base uppercase tracking-[0.16em] xl:text-2xl">
              {open ? BLOCK_TITLES[open] : ""}
            </SheetTitle>
          </SheetHeader>
          {/* Wider gutters and a centred measure so the sheet uses a 13"+
              screen instead of hugging the bottom-left corner. */}
          <div className="mx-auto w-full max-w-[1400px] px-4 pb-6 xl:px-10 xl:pb-10">
            {open && <BlockEditor block={open} />}
          </div>
        </SheetContent>
      </Sheet>
    </main>
    </>
  );
}
