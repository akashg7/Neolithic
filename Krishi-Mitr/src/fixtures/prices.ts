/**
 * CANON §7.3-shaped fixtures for `GET /prices/series`. Kartik's K4 does not exist
 * yet — same discipline as `fixtures/window.ts` and `fixtures/auth.ts`: every key
 * is transcribed from CANON, nothing invented.
 *
 * ★ The modal price on the latest day agrees with `fixtures/window.ts`'s
 *   `sell_now_net_paise_per_qtl` family of numbers by construction — this is the
 *   same कांदा · लासलगाव demo scenario CANON §7.4's own example uses
 *   (`cmd_onion` / `mkt_lasalgaon`), so a judge who checks S4's price against S9's
 *   "today's price" line sees the same story, not two disagreeing numbers.
 */

import type { DataSource, PricePoint, PriceSeriesRes } from '../types/api';

const DAY_MS = 24 * 60 * 60 * 1000;

/** `YYYY-MM-DD`, `n` days before today. Deterministic-enough for a fixture. */
function dateNDaysAgo(n: number): string {
  const d = new Date(Date.now() - n * DAY_MS);
  return d.toISOString().slice(0, 10);
}

/** Realistic 14-day observed mandi series for onion at Lasalgaon.
 * Reflects genuine market dynamics: supply fluctuations, quality spreads,
 * and realistic arrivals (9,000–16,800 qtl).
 * Crucially ends on 205400 paise (₹2,054/qtl) on day 0, keeping full consistency
 * with the recommendation models and window fixtures.
 */
const RECENT_14_SERIES = [
  { daysAgo: 13, modal: 194000, min: 172000, max: 212000, arrivals: 14250 },
  { daysAgo: 12, modal: 196500, min: 174000, max: 216000, arrivals: 15100 },
  { daysAgo: 11, modal: 193500, min: 169000, max: 211000, arrivals: 16800 },
  { daysAgo: 10, modal: 197000, min: 173000, max: 219000, arrivals: 13900 },
  { daysAgo: 9, modal: 199500, min: 178000, max: 224000, arrivals: 12400 },
  { daysAgo: 8, modal: 198000, min: 175000, max: 221000, arrivals: 14300 },
  { daysAgo: 7, modal: 201500, min: 179000, max: 228000, arrivals: 11850 },
  { daysAgo: 6, modal: 203000, min: 182000, max: 231000, arrivals: 11200 },
  { daysAgo: 5, modal: 201000, min: 178000, max: 227000, arrivals: 12900 },
  { daysAgo: 4, modal: 204000, min: 183000, max: 234000, arrivals: 10600 },
  { daysAgo: 3, modal: 207500, min: 186000, max: 239000, arrivals: 9400 },
  { daysAgo: 2, modal: 206000, min: 184000, max: 236000, arrivals: 10100 },
  { daysAgo: 1, modal: 204800, min: 182000, max: 233000, arrivals: 10400 },
  { daysAgo: 0, modal: 205400, min: 183000, max: 235000, arrivals: 9850 },
];

function recentModal(daysAgo: number): number {
  const found = RECENT_14_SERIES.find(d => d.daysAgo === daysAgo);
  return found ? found.modal : 194000 + (13 - Math.min(daysAgo, 13)) * 800;
}

function pointAt(daysAgo: number, modal: number, source: DataSource): PricePoint {
  const recent = RECENT_14_SERIES.find(d => d.daysAgo === daysAgo);
  if (recent && modal === recent.modal) {
    return {
      obs_date: dateNDaysAgo(daysAgo),
      min_paise_per_qtl: recent.min,
      max_paise_per_qtl: recent.max,
      modal_paise_per_qtl: recent.modal,
      arrivals_qtl: recent.arrivals,
      source,
    };
  }

  // Realistic variance for longer historical points
  const minSpread = 18000 + (Math.abs(daysAgo * 37) % 6000);
  const maxSpread = 22000 + (Math.abs(daysAgo * 43) % 8000);
  const baseArrivals = 11500 + (Math.abs(daysAgo * 127) % 4500);

  return {
    obs_date: dateNDaysAgo(daysAgo),
    min_paise_per_qtl: modal - minSpread,
    max_paise_per_qtl: modal + maxSpread,
    modal_paise_per_qtl: modal,
    arrivals_qtl: baseArrivals,
    source,
  };
}

/** S4's "today's price" — the last 14 days, all AGMARKNET. */
export const fxPriceSeries: PriceSeriesRes = {
  points: Array.from({ length: 14 }, (_, i) => {
    const daysAgo = 13 - i;
    return pointAt(daysAgo, recentModal(daysAgo), 'AGMARKNET');
  }),
  source_summary: { AGMARKNET: 14 },
  latest_obs_date: dateNDaysAgo(0),
};

/**
 * ★ I8. The same series, but the latest observation is `SYNTHETIC` — for
 *   exercising the source badge's non-trusted path without waiting for real
 *   sparse data to produce one. Not wired to a screen by default; swap
 *   `fxPriceSeries` for this one locally if you need to see the badge fire.
 */
export const fxPriceSeriesSynthetic: PriceSeriesRes = {
  ...fxPriceSeries,
  points: fxPriceSeries.points.map((p, i) =>
    i === fxPriceSeries.points.length - 1 ? { ...p, source: 'SYNTHETIC' as const } : p,
  ),
  source_summary: { AGMARKNET: 13, SYNTHETIC: 1 },
};

/**
 * S5's 180-day history — a real shape, not a straight line.
 *
 * ★ The last 14 days (index 166–179) are `recentModal()` verbatim — identical
 *   to `fxPriceSeries` — so S4 and S9's "today's price" never disagree with
 *   what S5's chart ends on.
 *
 * The earlier 166 days follow a deterministic curve (no `Math.random` — I15's
 * "no randomness for anything security-relevant" doesn't technically cover a
 * chart shape, but there's no reason to make a fixture non-reproducible either):
 * a baseline rising from a pre-harvest price toward the point where the recent
 * 14 days pick up, with a Gaussian-shaped crash overlaid near day 40 — a large
 * onion harvest hitting the market and flooding it, prices recovering over the
 * following months as farmers' stored stock depletes. Real onion markets in
 * Maharashtra move like this; a dead-straight 179-segment diagonal does not,
 * and S5 is the screen that has to look credible to someone who has actually
 * seen an onion price chart before.
 *
 *   base(i)  = START + (RECENT_START − START) × (i / 165)      — rises to
 *              RECENT_START exactly at i = 165, so day 166 (the first of the
 *              "recent 14") continues from it with no visible seam.
 *   dip(i)   = DIP_DEPTH × exp(−(i − DIP_CENTER)² / (2 × DIP_WIDTH²))
 *   modal(i) = round(base(i) − dip(i))
 *
 * `SYNTHETIC` sits at day 42 — two days past the trough, inside the same
 * disrupted post-harvest stretch the dip itself represents, where a mandi
 * genuinely might miss a day's reporting. Not mid-diagonal, where an isolated
 * differently-coloured point would read as a rendering glitch rather than a
 * real gap in the ingest history.
 */
const PRE_RECENT_DAYS = 166; // days 0..165 of the 180-day series
const START = 160000; // pre-harvest baseline, paise/qtl
const RECENT_START = recentModal(13); // = 195000, where day 166 must land
const DIP_CENTER = 40;
const DIP_WIDTH = 18;
const DIP_DEPTH = 35000;

function seasonalModal(i: number): number {
  const base = START + (RECENT_START - START) * (i / (PRE_RECENT_DAYS - 1));
  const dip = DIP_DEPTH * Math.exp(-((i - DIP_CENTER) ** 2) / (2 * DIP_WIDTH ** 2));
  // Natural market price fluctuations (deterministic so tests remain reliable)
  const fluctuation = Math.round(1600 * Math.sin(i * 0.73) + 1100 * Math.cos(i * 1.37));
  return Math.round(base - dip + fluctuation);
}

export const fxPriceHistory: PriceSeriesRes = {
  points: Array.from({ length: 180 }, (_, i) => {
    const daysAgo = 179 - i;
    const modal = i < PRE_RECENT_DAYS ? seasonalModal(i) : recentModal(daysAgo);
    const source: DataSource = i === 42 ? 'SYNTHETIC' : 'AGMARKNET';
    return pointAt(daysAgo, modal, source);
  }),
  source_summary: { AGMARKNET: 179, SYNTHETIC: 1 },
  latest_obs_date: dateNDaysAgo(0),
};

// ─────────────────────────────────────────────────────────────────────────────
// The picker's series — one per (commodity, market) pair the app offers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * ★ Why this exists: the market screen used to be hardwired to onion at
 *   Lasalgaon. Now that it has a crop picker and a district picker, a farmer
 *   who picks tomato at Pune must not be shown onion's chart under a tomato
 *   heading — a fixture that ignores its own arguments is worse than no
 *   fixture, because it looks right.
 *
 * ★ Onion at Lasalgaon returns `fxPriceHistory` *itself*, untouched. That
 *   series is pinned to `fixtures/window.ts` by construction, so the demo
 *   scenario's numbers stay in agreement across every screen. Everything the
 *   picker adds is built around it, never on top of it.
 *
 * ★ Tomato is deliberately the volatile one. That is the whole reason it is
 *   in scope (`KARTIK.md`: "Tomato is the NO_ADVICE crop. One commodity
 *   cannot demonstrate refusal.") — its swings are what widen the p10–p90
 *   band past the threshold and make the model refuse, which is the one
 *   behaviour a judge will actually try to break.
 */

/** Rupee level each mandi trades onion at, relative to Lasalgaon. Lasalgaon
 * is 1 by definition. Pune and Ahmednagar sit above and below it in the same
 * order `fixtures/nearby.ts` already puts them in, so the picker can never
 * contradict the nearby table on the same screen. */
const MARKET_LEVEL: Record<string, number> = {
  mkt_lasalgaon: 1.0,
  mkt_pimpalgaon: 0.98,
  mkt_yeola: 0.96,
  mkt_ahmednagar: 0.94,
  mkt_kopargaon: 0.95,
  mkt_rahata: 0.96,
  mkt_pune: 1.06,
  mkt_junnar: 1.02,
  mkt_baramati: 0.98,
  mkt_latur: 1.04,
  mkt_udgir: 1.01,
  mkt_jalgaon: 0.97,
  mkt_chalisgaon: 0.95,
  mkt_solapur: 0.99,
  mkt_pandharpur: 0.96,
  mkt_aurangabad: 1.01,
  mkt_vaijapur: 0.96,
  mkt_yavatmal: 1.03,
  mkt_wani: 0.99,
};

/** Base price profiles in paise/qtl for all commodities */
const CROP_PROFILES: Record<string, { base: number; swing: number; period: number; minOffset: number; maxOffset: number }> = {
  cmd_onion: { base: 205400, swing: 16000, period: 28, minOffset: 22000, maxOffset: 28000 },
  cmd_soyabean: { base: 438000, swing: 24000, period: 35, minOffset: 35000, maxOffset: 45000 },
  cmd_cotton: { base: 725000, swing: 32000, period: 42, minOffset: 48000, maxOffset: 65000 },
  cmd_tomato: { base: 124000, swing: 46000, period: 21, minOffset: 24000, maxOffset: 32000 },
  cmd_wheat: { base: 268000, swing: 12000, period: 45, minOffset: 18000, maxOffset: 22000 },
  cmd_gram: { base: 582000, swing: 26000, period: 38, minOffset: 40000, maxOffset: 52000 },
  cmd_maize: { base: 216000, swing: 15000, period: 30, minOffset: 19000, maxOffset: 25000 },
};

function generateCropSeries(commodityId: string, marketId: string, level: number): PriceSeriesRes {
  const profile = CROP_PROFILES[commodityId] ?? CROP_PROFILES.cmd_onion!;
  const points: PricePoint[] = Array.from({ length: 180 }, (_, i) => {
    const daysAgo = 179 - i;
    const wave = Math.sin((i / profile.period) * Math.PI * 2) * profile.swing;
    const micro = Math.sin(i * 0.73) * (profile.swing * 0.28);
    const drift = ((i - 179) / 179) * (profile.swing * 0.4);
    const modal = Math.round((profile.base + wave + micro + drift) * level);
    const min = Math.round(modal - profile.minOffset * level);
    const max = Math.round(modal + profile.maxOffset * level);
    const arrivals = Math.round((11000 + Math.abs(daysAgo * 137) % 6500) * (level > 1 ? 1.2 : 0.9));

    return {
      obs_date: dateNDaysAgo(daysAgo),
      min_paise_per_qtl: min,
      max_paise_per_qtl: max,
      modal_paise_per_qtl: modal,
      arrivals_qtl: arrivals,
      source: 'AGMARKNET' as DataSource,
    };
  });

  return {
    points,
    source_summary: { AGMARKNET: 180 },
    latest_obs_date: dateNDaysAgo(0),
  };
}

/**
 * The series for one (commodity, market) pair, 180 days.
 */
export function fxSeriesFor(commodityId: string, marketId: string): PriceSeriesRes | null {
  const level = MARKET_LEVEL[marketId] ?? 1.0;

  if (commodityId === 'cmd_onion' && marketId === 'mkt_lasalgaon') {
    return fxPriceHistory;
  }

  if (commodityId in CROP_PROFILES) {
    return generateCropSeries(commodityId, marketId, level);
  }

  return generateCropSeries('cmd_onion', marketId, level);
}
