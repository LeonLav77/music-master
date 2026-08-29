import { useCallback, useRef } from "react";
import { useKatana } from "@/lib/katana/store";

type Opts = {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  /** Parameter being dragged. Held for the duration so the amp's own
   *  updates do not yank the control out from under the finger. */
  holdKey?: string;
  /** px of travel for the full range */
  travel?: number;
  axis?: "y" | "x";
  step?: number;
};

/** Pointer drag -> value. Works with mouse, pen and touch. */
export function useDragValue({
  value,
  min,
  max,
  onChange,
  holdKey,
  travel = 220,
  axis = "y",
  step = 1,
}: Opts) {
  const startRef = useRef({ p: 0, v: 0 });
  const { hold } = useKatana();

  const onPointerDown = useCallback(
    (ev: React.PointerEvent) => {
      (ev.target as Element).setPointerCapture?.(ev.pointerId);
      startRef.current = { p: axis === "y" ? ev.clientY : ev.clientX, v: value };
      if (holdKey) hold(holdKey, true);
    },
    [axis, hold, holdKey, value],
  );

  const onPointerMove = useCallback(
    (ev: React.PointerEvent) => {
      if (!(ev.target as Element).hasPointerCapture?.(ev.pointerId)) return;
      const cur = axis === "y" ? ev.clientY : ev.clientX;
      const delta = axis === "y" ? startRef.current.p - cur : cur - startRef.current.p;
      const raw = startRef.current.v + (delta / travel) * (max - min);
      const snapped = Math.round(raw / step) * step;
      const next = Math.min(max, Math.max(min, snapped));
      if (next !== value) onChange(next);
    },
    [axis, max, min, onChange, step, travel, value],
  );

  const onPointerUp = useCallback(
    (ev: React.PointerEvent) => {
      (ev.target as Element).releasePointerCapture?.(ev.pointerId);
      if (holdKey) hold(holdKey, false);
    },
    [hold, holdKey],
  );

  const onKeyDown = useCallback(
    (ev: React.KeyboardEvent) => {
      const big = (max - min) / 10;
      const map: Record<string, number> = {
        ArrowUp: step,
        ArrowRight: step,
        ArrowDown: -step,
        ArrowLeft: -step,
        PageUp: big,
        PageDown: -big,
      };
      const d = map[ev.key];
      if (d === undefined) return;
      ev.preventDefault();
      onChange(Math.min(max, Math.max(min, Math.round(value + d))));
    },
    [max, min, onChange, step, value],
  );

  return { onPointerDown, onPointerMove, onPointerUp, onKeyDown };
}
