import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { RefreshCw, FolderOpen } from "lucide-react";
import { useKatana } from "@/lib/katana/store";
import { transport } from "@/lib/katana/transport";
import { EQ_BANDS } from "@/lib/katana/schema";
import { AmpDial } from "./AmpDial";
import { ChannelRail } from "./ChannelRail";
import { EqDock } from "./EqPad";
import { FootswitchRow } from "./FootswitchRow";
import { Knob } from "./Knob";
import { StompTile } from "./StompTile";
import { Treadle } from "./Treadle";
import { BlockEditor, BLOCK_TITLES, type BlockId } from "./BlockEditor";
import { AMP_KNOBS, buildBlocks } from "./surface-shared";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { BusyBar } from "./BusyBar";
import { ConnectionDot } from "./ConnectionDot";

function Screw({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "hardware-screw absolute h-2.5 w-2.5 rounded-full after:absolute after:inset-x-[2px] after:top-1/2 after:h-px after:-translate-y-1/2 after:bg-metal-dark",
        className,
      )}
    />
  );
}

/** Layout dedicated to the 9-inch landscape panel bolted next to the amp head. */
export function DeskSurface() {
  const k = useKatana();
  const [open, setOpen] = useState<BlockId | null>(null);
  const eqValues = Object.fromEntries(EQ_BANDS.map((b) => [b.key, k.num(b.key)]));
  const blocks = buildBlocks(k);
  // Local to the tube glow - not the store's `live` (amp has been read).
  const glowing = k.bool("bright") || k.dirty;

  return (
    <>
      <BusyBar label={k.busy} />
    <main className="amp-scene min-h-screen w-full overflow-y-auto bg-background p-2 landscape:h-screen landscape:overflow-hidden">
      <div className="amp-tolex amp-tilt relative flex min-h-[calc(100vh-1rem)] flex-col gap-2 rounded-[10px] p-2 landscape:h-full landscape:min-h-0">
        {/* chrome cabinet trim */}
        <span aria-hidden className="chrome-edge pointer-events-none absolute inset-x-3 top-0 h-[3px] rounded-b" />
        <span aria-hidden className="chrome-edge pointer-events-none absolute inset-x-3 bottom-0 h-[3px] rounded-t" />

        {/* ---- top control plate: badge + amp section ---- */}
        <section className="amp-plate relative grid shrink-0 grid-cols-[auto_auto_minmax(0,1fr)] items-center gap-4 rounded-[6px] px-4 py-2">
          <Screw className="left-1.5 top-1.5" />
          <Screw className="right-1.5 top-1.5" />
          <Screw className="left-1.5 bottom-1.5" />
          <Screw className="right-1.5 bottom-1.5" />

          <div className="flex items-center gap-3">
            <span className="relative grid h-6 w-6 place-items-center">
              <span
                aria-hidden
                className={cn("tube-glow tube-flicker absolute inset-[-8px]", !glowing && "opacity-40")}
              />
              <span className="relative h-3.5 w-3.5 rounded-full border border-metal-dark bg-ember shadow-[0_0_12px_var(--ember)]" />
            </span>
            <div className="leading-none">
              <h1 className="engrave font-display text-base uppercase tracking-[0.3em]">Katana</h1>
              <span className="engrave font-mono text-[0.5rem] uppercase tracking-[0.4em]">MkII · 100W</span>
            </div>
          </div>

          <div className="h-9 w-px bg-metal-dark/80" />

          <div className="flex min-w-0 items-center gap-3">
            <span className="engrave min-w-0 truncate font-mono text-[0.62rem] uppercase tracking-[0.2em]">
              {k.channelNames[k.channel]}
              {k.dirty && <span className="text-ember"> · edited</span>}
            </span>
            <div className="ml-auto flex shrink-0 items-center gap-2">
              <ConnectionDot state={k.connection} />
              <span className="engrave font-mono text-[0.52rem] uppercase tracking-[0.16em]">
                {k.lastSync
                  ? `synced ${k.lastSync.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                  : "never synced"}
              </span>
              <button
                type="button"
                onClick={k.resync}
                className="flex items-center gap-1.5 rounded-[3px] border border-metal-dark bg-[linear-gradient(180deg,var(--panel-raised),var(--metal-dark))] px-2.5 py-1.5 font-mono text-[0.6rem] uppercase tracking-[0.18em] text-steel shadow-[0_2px_0_oklch(0_0_0/70%)] active:translate-y-[1px] active:shadow-none"
              >
                <RefreshCw className={cn("h-3 w-3", k.syncing && "animate-spin")} />
                resync
              </button>
              <Link
                to="/patches"
                className="flex items-center gap-1.5 rounded-[3px] border border-metal-dark bg-[linear-gradient(180deg,var(--panel-raised),var(--metal-dark))] px-2.5 py-1.5 font-mono text-[0.6rem] uppercase tracking-[0.18em] text-foreground/70 shadow-[0_2px_0_oklch(0_0_0/70%)] active:translate-y-[1px] active:shadow-none"
              >
                <FolderOpen className="h-3 w-3" />
                patches
              </Link>
            </div>
          </div>
        </section>

        <div className="shrink-0">
          <ChannelRail
            current={k.channel}
            names={k.channelNames}
            onSelect={k.selectChannel}
            onSave={k.saveToChannel}
            variant="rail"
          />
        </div>

        {/* ---- cabinet body ---- */}
        <section className="grid min-h-0 flex-1 grid-cols-1 gap-2 min-[1000px]:grid-cols-[minmax(0,1.75fr)_minmax(0,1.15fr)_212px]">
          {/* amp control plate — primary */}
          <div className="amp-plate relative grid min-h-0 min-w-0 grid-cols-1 items-center justify-items-center gap-4 rounded-[6px] p-3 min-[720px]:grid-cols-[auto_minmax(0,1fr)]">
            <Screw className="left-1.5 top-1.5" />
            <Screw className="right-1.5 top-1.5" />
            <Screw className="left-1.5 bottom-1.5" />
            <Screw className="right-1.5 bottom-1.5" />
            <AmpDial value={k.num("amp_type")} onChange={(i) => k.set("amp_type", i)} size={180} />
            <div className="grid min-w-0 grid-cols-3 items-start justify-items-center gap-x-2 gap-y-1">
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
              <Knob label="Knob Vol" value={k.num("knob_volume")} size="md" disabled />

              <button
                type="button"
                onClick={() => k.toggle("bright")}
                aria-pressed={k.bool("bright")}
                className={cn(
                  "self-center rounded-[3px] border border-metal-dark px-3 py-2.5 font-display text-xs uppercase tracking-[0.18em] shadow-[0_3px_0_oklch(0_0_0/75%)] transition-transform active:translate-y-[2px] active:shadow-none",
                  k.bool("bright")
                    ? "bg-[linear-gradient(180deg,color-mix(in_oklab,var(--steel)_35%,var(--panel-raised)),var(--panel))] text-steel shadow-glow-steel"
                    : "bg-[linear-gradient(180deg,var(--panel-raised),var(--metal-dark))] text-foreground/60",
                )}
              >
                bright
              </button>
            </div>
          </div>

          {/* pedalboard standing on the cabinet floor, grille cloth behind */}
          <div className="amp-grille relative flex min-h-0 min-w-0 flex-col gap-2 rounded-[6px] p-2">
            <div className="grid min-h-0 flex-1 grid-cols-2 grid-rows-3 gap-2">
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
            </div>
            <FootswitchRow
              isOn={(block) => (block ? k.bool(block) : false)}
              onPress={(cc, block) => {
                // One command, not two: toggling the parameter already
                // switches the block on the amp. Sending the CC as well
                // would fight it, and CC 127 always means "on" - pressing
                // an active footswitch would desync the UI.
                if (block) k.toggle(block);
                else transport.sendCC(cc, 127);
              }}
            />
          </div>

          {/* wah riser */}
          <div className="amp-tolex relative flex min-h-[280px] flex-col rounded-[6px] border border-metal-dark/60 p-2 min-[1000px]:min-h-0">
            <span aria-hidden className="chrome-edge pointer-events-none absolute inset-x-2 top-0 h-[2px]" />
            <Treadle
              value={k.num("wah_position")}
              min={k.num("wah_pedal_min")}
              max={k.num("wah_pedal_max")}
              on={k.bool("pedal_switch")}
              onChange={(v) => k.set("wah_position", v)}
              onToggle={() => k.setWah(!k.bool("pedal_switch"))}
              onSweep={() => transport.sweepWah(k.num("wah_pedal_min"), k.num("wah_pedal_max"), 900)}
              onSetup={() => setOpen("wah")}
              className="min-h-0 flex-1"
            />
          </div>
        </section>
      </div>

      {/* Anchored bottom-right, clear of the footswitch row it used to cover. */}
      <div className="fixed bottom-3 right-3 z-50">
        <EqDock
          values={eqValues}
          on={k.bool("eq_switch")}
          onToggle={() => k.toggle("eq_switch")}
          onChange={(key, v) => k.set(key, v)}
          onFlat={() => EQ_BANDS.forEach((b) => k.set(b.key, 0))}
          onSetup={() => setOpen("eq")}
          height={190}
        />
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
