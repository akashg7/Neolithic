/**
 * One continuous picture: what the rate did, today, and the range it may take.
 * History bars-as-line on the left, the p10–p90 band opening out on the right.
 */
import React, { useMemo, useRef, useState } from 'react';
import type { MarketOverview } from '../lib/api';
import { useSay } from './kit';

const W = 760, H = 320, L = 8, R = 70, T = 18, B = 34;

export function PriceChart({ o, days }: { o: MarketOverview; days: number }) {
  const { rs, day, s } = useSay();
  const box = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const m = useMemo(() => {
    const hist = o.history.slice(-days).map(p => ({ date: p.obs_date, v: p.modal_paise_per_qtl, lo: null as number | null, hi: null as number | null }));
    const fut = o.forecast.points.map(p => ({ date: p.target_date, v: p.p50_paise_per_qtl, lo: p.p10_paise_per_qtl as number | null, hi: p.p90_paise_per_qtl as number | null }));
    const all = [...hist, ...fut];
    const t = all.map(p => Date.parse(p.date));
    const t0 = Math.min(...t), t1 = Math.max(...t);
    const vals = all.flatMap(p => [p.v, p.lo ?? p.v, p.hi ?? p.v]);
    const span = Math.max(...vals) - Math.min(...vals) || 1;
    const lo = Math.min(...vals) - span * 0.1, hi = Math.max(...vals) + span * 0.08;
    const x = (i: number) => L + ((t[i]! - t0) / (t1 - t0 || 1)) * (W - L - R);
    const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    const k = hist.length;
    const path = (idx: number[], f: (i: number) => number) => idx.map((i, j) => `${j ? 'L' : 'M'}${x(i).toFixed(1)} ${y(f(i)).toFixed(1)}`).join('');
    const hi_ = all.map((_, i) => i).slice(0, k);
    const fi = all.map((_, i) => i).slice(Math.max(0, k - 1));
    const band = fi.length > 1 ? `${path(fi, i => all[i]!.hi ?? all[i]!.v)}${[...fi].reverse().map(i => `L${x(i).toFixed(1)} ${y(all[i]!.lo ?? all[i]!.v).toFixed(1)}`).join('')}Z` : '';
    const ticks = [0, 1, 2, 3].map(i => lo + ((i + 0.5) / 4) * (hi - lo));
    return { all, k, x, y, histPath: path(hi_, i => all[i]!.v), futPath: path(fi, i => all[i]!.v), band, ticks };
  }, [o, days]);

  if (m.k === 0) return null;
  const now = m.k - 1;
  const end = m.all.length - 1;
  const h = hover != null ? m.all[hover] : null;
  const move = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = 0;
    m.all.forEach((_, i) => { if (Math.abs(m.x(i) - px) < Math.abs(m.x(best) - px)) best = i; });
    setHover(best);
  };

  return (
    <>
      <div className="km-chart" ref={box} onPointerMove={move} onPointerLeave={() => setHover(null)}>
        {h ? (
          <div className="km-tip" style={{ left: `${Math.min(84, Math.max(16, (m.x(hover!) / W) * 100))}%` }}>
            {day(h.date)}: <b>{rs(h.v)}</b>
            {h.lo != null ? <><br />{s('शक्यता', 'संभावना', 'Range')} {rs(h.lo)} – {rs(h.hi)}</> : null}
          </div>
        ) : null}
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={s('भावाचा आलेख आणि पुढील १४ दिवसांचा अंदाज', 'भाव का ग्राफ और अगले 14 दिन का अनुमान', 'Price history and 14-day forecast')}>
          {m.ticks.map((v, i) => (
            <g key={i}>
              <line x1={L} x2={W - R} y1={m.y(v)} y2={m.y(v)} stroke="var(--line)" />
              <text x={W - R + 10} y={m.y(v) + 4}>{rs(Math.round(v / 1000) * 1000)}</text>
            </g>
          ))}
          {m.band ? <path d={m.band} fill="#006146" opacity={0.13} /> : null}
          <path d={m.histPath} fill="none" stroke="var(--brand2)" strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
          <path d={m.futPath} fill="none" stroke="var(--good)" strokeWidth={3} strokeDasharray="2 7" strokeLinecap="round" />
          <line x1={m.x(now)} x2={m.x(now)} y1={T} y2={H - B} stroke="var(--ink2)" strokeDasharray="3 4" opacity={0.55} />
          <circle cx={m.x(now)} cy={m.y(m.all[now]!.v)} r={6.5} fill="var(--brand2)" stroke="#fff" strokeWidth={3} />
          {h ? <circle cx={m.x(hover!)} cy={m.y(h.v)} r={5.5} fill="var(--ink)" stroke="#fff" strokeWidth={2} /> : null}
          <text x={L} y={H - 8}>{day(m.all[0]!.date)}</text>
          <text x={m.x(now)} y={H - 8} textAnchor="middle">{s('आता', 'अब', 'Now')}</text>
          {end > now ? <text x={m.x(end)} y={H - 8} textAnchor="end">{day(m.all[end]!.date)}</text> : null}
        </svg>
      </div>
      <div className="km-legend">
        <span><i style={{ borderColor: 'var(--brand2)' }} />{s('झालेला भाव', 'पिछला भाव', 'Past rate')}</span>
        {end > now ? <span><i style={{ borderColor: 'var(--good)', borderTopStyle: 'dotted' }} />{s('अंदाज', 'अनुमान', 'Forecast')}</span> : null}
        {end > now ? <span><i style={{ borderTopWidth: 12, borderColor: 'rgba(0,97,70,.18)' }} />{s('१० पैकी ८ वेळा भाव या पट्ट्यात', '10 में से 8 बार भाव इस पट्टी में', 'Rate falls here 8 times in 10')}</span> : null}
      </div>
    </>
  );
}
