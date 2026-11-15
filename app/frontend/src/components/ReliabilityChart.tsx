"use client";

// Reliability chart: for founders grouped by the chance they were given, the share that actually
// succeeded. Dots on the dashed diagonal mean honest odds. One series, so no legend: the heading names it.
// A strip below shows how many founders each band holds, so thin parts of the chart are visible.
// Drawn at the container's pixel width (text stays readable on phones); every dot has a tooltip on
// hover, focus or tap (a tap fires focus then click, so click only ever shows it; moving away hides it),
// and the same numbers are in a table underneath.
import { useEffect, useRef, useState } from "react";

import { cx } from "@/components/ui";

export interface Bin {
  low: number;
  high: number;
  count: number;
  predicted: number;
  observed: number;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

export function ReliabilityChart({ bins }: { bins: Bin[] }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  const max = Math.min(1, Math.max(0.5, Math.ceil(Math.max(...bins.map((b) => Math.max(b.high, b.observed))) * 10) / 10));
  const m = { top: 14, right: 16, bottom: 42, left: 58 };
  const plotW = Math.max(0, width - m.left - m.right);
  const plotH = Math.min(plotW, 340);
  const stripH = 56;
  const stripLabel = m.top + plotH + m.bottom + 16; // the strip's own title sits clear of the x-axis title
  const height = stripLabel + 8 + stripH + 20;
  const x = (v: number) => m.left + (v / max) * plotW;
  const y = (v: number) => m.top + plotH - (v / max) * plotH;
  const ticks = Array.from({ length: Math.round(max * 10) + 1 }, (_, i) => i / 10);
  const most = Math.max(...bins.map((b) => b.count));
  const stripTop = stripLabel + 8;
  const a = active === null ? null : bins[active];

  return (
    <figure className="m-0">
      <div ref={ref} className="relative w-full select-none" onMouseLeave={() => setActive(null)}>
        {width > 0 && (
          <svg width={width} height={height} role="img" aria-label="Reliability chart: the share of founders who succeeded, against the chance they were given">
            {ticks.map((t) => (
              <g key={t}>
                <line x1={m.left} x2={m.left + plotW} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
                <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-[var(--faint)] text-[11.5px] tabular">
                  {pct(t)}
                </text>
                <text x={x(t)} y={m.top + plotH + 18} textAnchor="middle" className="fill-[var(--faint)] text-[11.5px] tabular">
                  {pct(t)}
                </text>
              </g>
            ))}
            <line x1={x(0)} y1={y(0)} x2={x(max)} y2={y(max)} stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="5 5" />
            {/* key for the diagonal, in the empty top-left corner (high success, low odds never happens) */}
            <line x1={m.left + 10} x2={m.left + 34} y1={m.top + 12} y2={m.top + 12} stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="5 5" />
            <text x={m.left + 40} y={m.top + 12} dy="0.32em" className="fill-[var(--muted)] text-[12px] font-semibold">
              Perfect odds
            </text>
            <text x={m.left + plotW / 2} y={m.top + plotH + 36} textAnchor="middle" className="fill-[var(--muted)] text-[12px] font-semibold">
              The chance it gave
            </text>
            <text transform={`translate(13 ${m.top + plotH / 2}) rotate(-90)`} textAnchor="middle" className="fill-[var(--muted)] text-[12px] font-semibold">
              Share who succeeded
            </text>

            {bins.map((b, i) => (
              <g key={b.low}>
                <line x1={x(b.predicted)} x2={x(b.predicted)} y1={y(b.predicted)} y2={y(b.observed)} stroke="var(--viz-o3)" strokeWidth={2} strokeOpacity={0.35} />
                <circle cx={x(b.predicted)} cy={y(b.observed)} r={active === i ? 7 : 5.5} fill="var(--viz-o3)" stroke="var(--surface)" strokeWidth={2} />
                <circle
                  cx={x(b.predicted)}
                  cy={y(b.observed)}
                  r={18}
                  fill="transparent"
                  tabIndex={0}
                  role="button"
                  aria-label={`Given about ${pct(b.predicted)}: ${pct(b.observed)} of ${b.count} founders succeeded`}
                  onMouseEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  onClick={() => setActive(i)}
                  className="cursor-pointer outline-none"
                />
              </g>
            ))}

            <text x={m.left} y={stripLabel} className="fill-[var(--muted)] text-[11.5px] font-semibold">
              Founders in each band
            </text>
            {bins.map((b, i) => {
              const bw = Math.max(4, (b.high - b.low) / max * plotW - 2);
              const h = Math.max(2, (b.count / most) * (stripH - 16));
              const top = stripTop + 8 + (stripH - 16 - h);
              return (
                <g key={`n${b.low}`} onMouseEnter={() => setActive(i)}>
                  <rect x={x(b.low) + 1} y={top} width={bw} height={h} rx={3} fill={active === i ? "var(--viz-o3)" : "var(--line-strong)"} />
                  <text x={x(b.low) + 1 + bw / 2} y={stripTop + stripH + 6} textAnchor="middle" className="fill-[var(--ink-2)] text-[11.5px] font-semibold tabular">
                    {b.count}
                  </text>
                </g>
              );
            })}
          </svg>
        )}
        {a && width > 0 && (
          <div
            role="status"
            className="pointer-events-none absolute z-10 w-[190px] rounded-[12px] bg-ink px-3 py-2 text-[13px] leading-snug text-bg shadow-float"
            style={{
              left: Math.min(Math.max(0, x(a.predicted) - 95), width - 190),
              top: Math.max(0, y(a.observed) - 74),
            }}
          >
            <span className="block font-bold">Given about {pct(a.predicted)}</span>
            {pct(a.observed)} of {a.count} founders succeeded
          </div>
        )}
      </div>
      <details className="mt-3 text-[14px]">
        <summary className="cursor-pointer font-semibold text-ink-2">Show as a table</summary>
        <table className="mt-2 w-full text-left tabular">
          <thead>
            <tr className="border-b border-line-strong text-[12.5px] text-muted">
              <th className="py-2 font-semibold">Chance given</th>
              <th className="py-2 font-semibold">Average</th>
              <th className="py-2 font-semibold">Succeeded</th>
              <th className="py-2 text-right font-semibold">Founders</th>
            </tr>
          </thead>
          <tbody>
            {bins.map((b) => (
              <tr key={b.low} className={cx("border-b border-line")}>
                <td className="py-2">
                  {pct(b.low)}–{pct(b.high)}
                </td>
                <td className="py-2">{pct(b.predicted)}</td>
                <td className="py-2 font-semibold">{pct(b.observed)}</td>
                <td className="py-2 text-right">{b.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
