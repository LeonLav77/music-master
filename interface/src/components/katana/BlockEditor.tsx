import { Knob } from "./Knob";
import { Segmented } from "./Segmented";
import { EqWall } from "./Eq";
import { Treadle } from "./Treadle";
import { useKatana } from "@/lib/katana/store";
import { transport } from "@/lib/katana/transport";
import {
  labelFor,
  FX_TYPE_OPTIONS,
  BOOST_TYPE_OPTIONS,
  DELAY_TYPE_OPTIONS,
  REVERB_TYPE_OPTIONS,
  WAH_TYPE_OPTIONS,
  PEDAL_MODE_OPTIONS,
  BOOST_PARAMS,
  EQ_BANDS,
  FX_PARAM_MAP,
  GATE_PARAMS,
  REVERB_PARAMS,
  delayParams,
  type ParamDef,
} from "@/lib/katana/schema";
import { cn } from "@/lib/utils";

export type BlockId = "boost" | "mod" | "fx" | "delay" | "reverb" | "gate" | "eq" | "wah";

export const BLOCK_TITLES: Record<BlockId, string> = {
  boost: "Boost / Overdrive",
  mod: "Mod — FX slot 1",
  fx: "FX — slot 2",
  delay: "Delay engines",
  reverb: "Reverb",
  gate: "Noise gate",
  eq: "Graphic EQ",
  wah: "Wah / Expression",
};

function KnobRow({ params, accent }: { params: ParamDef[]; accent?: "steel" | "ember" }) {
  const { num, set } = useKatana();
  // auto-fit stretched three knobs across the full width; auto-fill with a
  // capped track keeps them grouped at their natural size instead.
  return (
    <div className="grid justify-items-center gap-x-4 gap-y-5 [grid-template-columns:repeat(auto-fit,minmax(84px,1fr))] xl:justify-start xl:gap-x-10 xl:gap-y-8 xl:[grid-template-columns:repeat(auto-fill,minmax(150px,max-content))]">
      {params
        .filter((p) => p.kind === "range")
        .map((p) => (
          <Knob
            key={p.key}
            label={p.label}
            paramKey={p.key}
            value={num(p.key)}
            min={p.min ?? 0}
            max={p.max ?? 100}
            accent={accent ?? "steel"}
            size="sm"
            onChange={(v) => set(p.key, v)}
          />
        ))}
    </div>
  );
}

function Toggle({ k, label }: { k: string; label: string }) {
  const { bool, toggle } = useKatana();
  const on = bool(k);
  return (
    <button
      type="button"
      onClick={() => toggle(k)}
      aria-pressed={on}
      className={cn(
        "rounded-[3px] border px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.18em] transition-colors xl:px-5 xl:py-3.5 xl:text-[0.74rem]",
        on
          ? "border-ember/70 bg-ember/10 text-ember"
          : "border-hairline bg-panel text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

function FxSlot({ slot }: { slot: 1 | 2 }) {
  const { num, set } = useKatana();
  const typeKey = `fx${slot}_type`;
  const type = num(typeKey);
  const name = labelFor(typeKey, type);
  const params = FX_PARAM_MAP[name];

  return (
    <div className="flex flex-col gap-4 xl:gap-7">
      <div>
        <span className="mb-2 block font-mono text-[0.6rem] uppercase tracking-[0.2em] text-muted-foreground xl:text-[0.72rem]">
          effect
        </span>
        <div className="grid gap-1 [grid-template-columns:repeat(auto-fit,minmax(92px,1fr))] xl:gap-2 xl:[grid-template-columns:repeat(auto-fit,minmax(140px,1fr))]">
          {FX_TYPE_OPTIONS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => set(typeKey, f.value)}
              aria-pressed={f.value === type}
              className={cn(
                "rounded-[3px] border px-2 py-2 text-center font-display text-[0.62rem] uppercase leading-tight tracking-[0.08em] transition-colors xl:py-3.5 xl:text-[0.76rem]",
                f.value === type
                  ? "border-steel bg-steel/15 text-steel shadow-glow-steel"
                  : "border-hairline bg-panel text-muted-foreground hover:text-foreground",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {params ? (
        <KnobRow params={params} />
      ) : (
        <p className="rounded-[3px] border border-dashed border-hairline bg-panel px-3 py-4 font-mono text-[0.68rem] text-muted-foreground">
          {name} is selectable but its parameters are not mapped — values read back as{" "}
          <span className="text-steel">unknown</span>, not zero.
        </p>
      )}
    </div>
  );
}

export function BlockEditor({ block }: { block: BlockId }) {
  const { num, set, bool, setWah } = useKatana();
  const eqValues = Object.fromEntries(EQ_BANDS.map((b) => [b.key, num(b.key)]));

  switch (block) {
    case "boost":
      return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] xl:gap-10">
          <Segmented
            label="pedal"
            options={BOOST_TYPE_OPTIONS}
            value={num("boost_type")}
            onChange={(i) => set("boost_type", i)}
            columns={5}
            size="sm"
          />
          <div className="flex flex-col gap-4 xl:gap-7">
            <KnobRow params={BOOST_PARAMS} accent="ember" />
            <div className="flex">
              <Toggle k="boost_solo_switch" label="Solo" />
            </div>
          </div>
        </div>
      );
    case "mod":
      return <FxSlot slot={1} />;
    case "fx":
      return <FxSlot slot={2} />;
    case "delay":
      return (
        <div className="grid gap-6 lg:grid-cols-2">
          {(["delay", "delay2"] as const).map((p) => (
            <div key={p} className="flex flex-col gap-3 rounded-[4px] border border-hairline p-3 xl:gap-5 xl:p-6">
              <div className="flex items-center justify-between">
                <span className="font-display text-sm uppercase tracking-[0.14em] xl:text-lg">
                  {p === "delay" ? "Delay 1" : "Delay 2"}
                </span>
                <Toggle k={`${p}_switch`} label={bool(`${p}_switch`) ? "on" : "off"} />
              </div>
              <Segmented
                options={DELAY_TYPE_OPTIONS}
                value={num(`${p}_type`)}
                onChange={(i) => set(`${p}_type`, i)}
                size="sm"
              />
              <KnobRow params={delayParams(p)} />
              <label className="flex items-center gap-3">
                <span className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-muted-foreground xl:text-[0.72rem]">
                  time
                </span>
                <input
                  type="range"
                  min={1}
                  max={2000}
                  value={num(`${p}_time`)}
                  onChange={(ev) => set(`${p}_time`, Number(ev.target.value))}
                  // 4px of track is not a touch target; the Pi panel is finger-driven.
                  className="h-6 flex-1 cursor-pointer appearance-none rounded bg-transparent accent-[var(--steel)] [&::-webkit-slider-runnable-track]:h-1.5 [&::-webkit-slider-runnable-track]:rounded [&::-webkit-slider-runnable-track]:bg-track [&::-webkit-slider-thumb]:mt-[-7px] [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-steel"
                />
                <span className="w-16 text-right font-mono text-xs tabular-nums text-steel xl:w-24 xl:text-base">
                  {num(`${p}_time`)} ms
                </span>
              </label>
            </div>
          ))}
        </div>
      );
    case "reverb":
      return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] xl:gap-10">
          <Segmented
            label="type"
            options={REVERB_TYPE_OPTIONS}
            value={num("reverb_type")}
            onChange={(i) => set("reverb_type", i)}
          />
          <KnobRow params={REVERB_PARAMS} />
        </div>
      );
    case "gate":
      return <KnobRow params={GATE_PARAMS} />;
    case "eq":
      return (
        <div className="flex flex-col gap-4 xl:gap-7">
          <div className="flex flex-wrap items-center gap-3 xl:gap-5">
            <Toggle k="eq_switch" label={bool("eq_switch") ? "EQ on" : "EQ off"} />
            <Toggle k="eq_type" label={bool("eq_type") ? "post" : "pre"} />
            <button
              type="button"
              onClick={() => EQ_BANDS.forEach((b) => set(b.key, 0))}
              className="rounded-[3px] border border-hairline px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground xl:px-5 xl:py-3.5 xl:text-[0.74rem]"
            >
              flat
            </button>
            <button
              type="button"
              onClick={() =>
                [14, 14, 12, -6, -12, -15, -7, 8, 10, 11].forEach((v, i) =>
                  set(EQ_BANDS[i]!.key, v),
                )
              }
              className="rounded-[3px] border border-hairline px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground xl:px-5 xl:py-3.5 xl:text-[0.74rem]"
            >
              mid scoop
            </button>
            <Knob
              label="EQ Level"
              paramKey="eq_level"
              value={num("eq_level")}
              max={48}
              size="sm"
              onChange={(v) => set("eq_level", v)}
            />
          </div>
          <EqWall values={eqValues} onChange={(k, v) => set(k, v)} />
        </div>
      );
    case "wah":
      return (
        <div className="flex flex-col gap-4 xl:gap-7">
          <Segmented
            label="voicing"
            options={WAH_TYPE_OPTIONS}
            value={num("wah_type")}
            onChange={(i) => set("wah_type", i)}
          />
          <Segmented
            label="pedal mode"
            options={PEDAL_MODE_OPTIONS}
            value={num("pedal_type")}
            onChange={(i) => set("pedal_type", i)}
          />
          {/* Explicit track for the treadle: `flex-wrap items-end` gave it no
              height to fill, which collapsed the whole pedal graphic. */}
          <div className="grid items-start gap-6 sm:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)] xl:items-center xl:gap-12">
            <Treadle
              value={num("wah_position")}
              min={num("wah_pedal_min")}
              max={num("wah_pedal_max")}
              on={bool("pedal_switch")}
              onChange={(v) => set("wah_position", v)}
              onToggle={() => setWah(!bool("pedal_switch"))}
              onSweep={() => transport.sweepWah(num("wah_pedal_min"), num("wah_pedal_max"), 900)}
            />
            <KnobRow params={WAH_KNOBS} />
          </div>
        </div>
      );
    default:
      return null;
  }
}

const WAH_KNOBS: ParamDef[] = [
  { key: "wah_pedal_min", label: "Min", kind: "range", min: 0, max: 100 },
  { key: "wah_pedal_max", label: "Max", kind: "range", min: 0, max: 100 },
  { key: "wah_level", label: "Level", kind: "range", min: 0, max: 100 },
  { key: "wah_direct_mix", label: "Direct", kind: "range", min: 0, max: 100 },
];
