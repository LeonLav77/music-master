import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, FileMusic } from "lucide-react";
import { cn } from "@/lib/utils";
import { BusyBar } from "@/components/katana/BusyBar";
import { labelFor } from "@/lib/katana/schema";
import { transport } from "@/lib/katana/transport";

export const Route = createFileRoute("/patches")({
  head: () => ({
    meta: [
      { title: "Tone Studio Patch Browser — Katana MkII" },
      {
        name: "description",
        content:
          "Browse .tsl files exported from BOSS Tone Studio, preview each patch's amp, boost, delay and reverb settings, and load 109 parameters to the amp.",
      },
      { property: "og:title", content: "Tone Studio Patch Browser — Katana MkII" },
      {
        property: "og:description",
        content: "List, inspect and load .tsl Tone Studio patches onto the Katana MkII.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Patches,
});

type PatchSettings = Record<string, number>;

type Patch = {
  file: string;
  index: number;
  name: string;
  settings: PatchSettings;
  eq?: number[];
};

type PatchFile = {
  file: string;
  patches?: { index: number; name: string; settings: PatchSettings; eq?: number[] }[];
  error?: string;
};

function Patches() {
  const [files, setFiles] = useState<PatchFile[]>([]);
  const [selected, setSelected] = useState<Patch | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    transport
      .patchFiles()
      .then((result) => {
        if (cancelled) return;
        setFiles(result as PatchFile[]);
        const first = result.find((f) => f.patches?.length)?.patches?.[0];
        const file = result.find((f) => f.patches?.length)?.file;
        if (first && file) {
          setSelected({ file, ...first } as Patch);
        }
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  const load = async () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const result = await transport.loadPatchFile(selected.file, selected.index);
      setLoaded(`${result.name} — ${result.applied} parameters`);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <BusyBar label={loading ? "loading patch" : null} />
    <main className="min-h-screen px-3 py-3">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-3">
        <header className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <div className="flex min-w-0 items-baseline gap-3">
            <h1 className="truncate font-display text-lg uppercase tracking-[0.22em]">
              Tone Studio Patches
            </h1>
            <span className="truncate font-mono text-[0.6rem] uppercase tracking-[0.2em] text-muted-foreground">
              .tsl · 109 parameters
            </span>
          </div>
          <Link
            to="/"
            className="flex shrink-0 items-center gap-1.5 rounded-[3px] border border-hairline px-2.5 py-1.5 font-mono text-[0.6rem] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            control
          </Link>
        </header>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-3">
            {files.map((f) => (
              <div key={f.file} className="rounded-[4px] border border-hairline bg-panel/60 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <FileMusic className="h-3.5 w-3.5 shrink-0 text-steel" />
                  <span className="truncate font-mono text-[0.68rem] text-steel">{f.file}</span>
                </div>
                <div className="grid gap-1.5 sm:grid-cols-2">
                  {(f.patches ?? []).map((p) => (
                    <button
                      key={`${f.file}:${p.index}`}
                      type="button"
                      disabled={loading}
                      onClick={() => setSelected({ file: f.file, ...p })}
                      className={cn(
                        "min-w-0 rounded-[3px] border px-2.5 py-2 text-left transition-colors disabled:opacity-50",
                        selected?.file === f.file && selected?.index === p.index
                          ? "border-ember bg-ember/10"
                          : "border-hairline bg-panel hover:border-steel/40",
                      )}
                    >
                      <span className="block truncate font-display text-sm uppercase tracking-[0.1em]">
                        {p.name}
                      </span>
                      <span className="block truncate font-mono text-[0.58rem] text-muted-foreground">
                        {labelFor("amp_type", p.settings["amp_type"] ?? 0)}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-[4px] border border-hairline bg-panel/60 p-4">
            {selected ? (
              <div className="flex flex-col gap-4">
                <div>
                  <h2 className="font-display text-xl uppercase tracking-[0.14em]">
                    {selected.name}
                  </h2>
                  <p className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-muted-foreground">
                    {selected.file}
                  </p>
                </div>
                <dl className="grid grid-cols-2 gap-2">
                  {[
                    ["Amp", labelFor("amp_type", selected.settings["amp_type"] ?? 0)],
                    ["Gain", String(selected.settings["gain"] ?? 0)],
                    [
                      "Boost",
                      selected.settings["boost_switch"]
                        ? labelFor("boost_type", selected.settings["boost_type"] ?? 0)
                        : "off",
                    ],
                    [
                      "Delay",
                      selected.settings["delay_switch"]
                        ? `${labelFor("delay_type", selected.settings["delay_type"] ?? 0)} · ${selected.settings["delay_time"] ?? 0}ms`
                        : "off",
                    ],
                    [
                      "Reverb",
                      selected.settings["reverb_switch"]
                        ? labelFor("reverb_type", selected.settings["reverb_type"] ?? 0)
                        : "off",
                    ],
                    [
                      "Tone",
                      `${selected.settings["bass"] ?? 0}/${selected.settings["middle"] ?? 0}/${selected.settings["treble"] ?? 0}`,
                    ],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="min-w-0 rounded-[3px] border border-hairline bg-panel px-2.5 py-2"
                    >
                      <dt className="font-mono text-[0.55rem] uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </dt>
                      <dd className="truncate font-display text-sm uppercase tracking-[0.08em] text-foreground">
                        {value}
                      </dd>
                    </div>
                  ))}
                </dl>
                <button
                  type="button"
                  onClick={load}
                  disabled={loading || !!error}
                  className="rounded-[3px] border border-ember bg-ember/15 px-4 py-3 font-display text-sm uppercase tracking-[0.18em] text-ember shadow-glow-ember disabled:opacity-60"
                >
                  {loading ? "loading…" : "load to amp"}
                </button>
                {loaded && !loading && (
                  <p className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-steel">
                    {loaded} loaded to panel
                  </p>
                )}
                {error && (
                  <p className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-ember">
                    {error}
                  </p>
                )}
              </div>
            ) : (
              <p className="font-mono text-xs text-muted-foreground">
                {files.length ? "Select a patch." : error ?? "Loading patch files…"}
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
    </>
  );
}
