# Amp schema

`generated.ts` is **generated** — do not edit it. It is written from the
Python parameter tables by `scripts/generate_schema.py`, so the UI and the
amp cannot disagree about ranges or, more importantly, enum numbering.

Regenerate after changing `katana_amp/katana.py`:

```bash
bun run schema
```

## Why enum values are not array indices

The amp's numbering is **sparse**. Effects skip 5, 8, 11, 13 and 17; boost
pedals skip 7. Treating the position in a label array as the value sends
the wrong number — picking "Phaser" would load Octave, "Uni-V" would load
AC Processor.

So every enum is `{value, label}[]` and widgets pass `option.value`, never
the index. `labelFor(key, value)` looks a name up the safe way.

`schema.ts` layers the interface's own decisions on top — display labels,
grouping and ordering — and re-exports everything from here.
