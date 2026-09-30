/**
 * CANON §7.4-shaped fixture for `GET /ai/forecast`. Nikhil's N2 does not exist
 * yet — same discipline as every other fixture in this app: every key comes from
 * CANON, nothing invented.
 *
 * ★ N2's own acceptance bar (PLAN.md) is `p10 <= p50 <= p90` on every horizon —
 *   this fixture is built by construction to satisfy that (p10/p90 are always
 *   `p50 ∓ a non-negative half-band`), and `forecast.test.ts` asserts it holds
 *   for all 14 points rather than trusting the construction blindly.
 *
 * The trend is a plausible continuation of `fixtures/prices.ts`'s history, and
 * the band widens with horizon — a forecast eleven days out is genuinely less
 * certain than one four days out, which is the whole reason `ForecastFan` draws
 * a fan and not a line.
 *
 * ★ CONTRACT GAP: CANON's `ForecastRes` has no `source` field at all — a
 *   forecast is a model output, not an observed price row, so "AGMARKNET vs
 *   SYNTHETIC" does not apply to it the way it does to `PricePoint`. PRANAY.md
 *   §2.7's rule 2 ("the source badge is part of the chart") reads as if every
 *   chart needs one; `ForecastFan` does not render one because there is nothing
 *   in this response to badge. Blocker filed to Nilesh/Nikhil.
 */

import type { ForecastPoint, ForecastRes } from '../types/api';

const DAY_MS = 24 * 60 * 60 * 1000;

function dateNDaysAhead(n: number): string {
  const d = new Date(Date.now() + n * DAY_MS);
  return d.toISOString().slice(0, 10);
}

/**
 * The median path.
 *
 * ★ This was `205000 + daysAhead * 1850` — a mathematically perfect straight
 *   line, drawn as a fourteen-day forecast corridor. Nobody who has seen a
 *   mandi price chart believes a ruler, and the people who will look hardest
 *   at this screen are exactly the people who have seen one. A model output
 *   that looks synthetic undermines the model even when the model is fine.
 *
 * ★ So: a rising trend, with a slow wave over it and a smaller faster one on
 *   top. Two periods that do not divide into each other never repeat inside
 *   the window, which is what stops it reading as a pattern. Every term is
 *   deterministic — no `Math.random`, so the fixture is reproducible and the
 *   tests below can assert on it.
 *
 * ★ The amplitudes are deliberately small against the drift. A forecast that
 *   swings wildly around its own median is not a more realistic forecast, it
 *   is a less confident one, and confidence is what the p10–p90 band is for.
 */
const FORECAST_START = 205000;
const FORECAST_DRIFT = 1850; // paise/qtl/day — the trend fxPriceHistory ends on
const SLOW_WAVE = 2200;
const FAST_WAVE = 900;

function forecastMedian(daysAhead: number): number {
  const trend = FORECAST_START + daysAhead * FORECAST_DRIFT;
  const slow = SLOW_WAVE * Math.sin((daysAhead / 9) * Math.PI * 2);
  const fast = FAST_WAVE * Math.sin((daysAhead / 3.5) * Math.PI * 2 + 1.1);
  return Math.round(trend + slow + fast);
}

function buildPoint(daysAhead: number): ForecastPoint {
  const p50 = forecastMedian(daysAhead);
  // The band still widens with horizon — that is the honest part, and it is
  // what makes the fan a fan rather than three parallel lines.
  const bandFraction = 0.05 + daysAhead * 0.012;
  const half = Math.round((p50 * bandFraction) / 2);
  return {
    target_date: dateNDaysAhead(daysAhead),
    p10_paise_per_qtl: p50 - half,
    p50_paise_per_qtl: p50,
    p90_paise_per_qtl: p50 + half,
  };
}

/**
 * 14 points, day 1 through day 14 ahead. Point index 10 (day 11 ahead) is the
 * same horizon `fixtures/window.ts`'s `fxHold` recommends holding to — the two
 * fixtures are telling the same demo story from two different screens.
 */
export const fxForecast: ForecastRes = {
  as_of_date: dateNDaysAhead(0),
  points: Array.from({ length: 14 }, (_, i) => buildPoint(i + 1)),
  model_card: { mase: 0.71, coverage_80_bps: 7840 },
};

// ─────────────────────────────────────────────────────────────────────────────
// The picker's forecast — one per (commodity, market) pair
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Same rule as `fxSeriesFor` in `fixtures/prices.ts`: once the market screen
 * has a crop picker and a district picker, a fixture that ignores which crop
 * was asked about is a fixture that lies convincingly.
 *
 * ★ Onion at Lasalgaon returns `fxForecast` itself, so the demo scenario's
 *   numbers stay pinned to `fixtures/window.ts`.
 *
 * ★ Tomato's band is wide on purpose, and it is wide because the history is:
 *   `fxSeriesFor('cmd_tomato', …)` swings ±46,000 paise on a 23-day cycle, and
 *   a quantile model fitted to that cannot produce a narrow interval. At day 14
 *   the band runs past 35% of p50 — `NO_ADVICE_BAND_THRESHOLD_BPS`, the
 *   server's refusal threshold — which is exactly the point. I6 is not a
 *   special case the app handles; it is the honest output for a crop that
 *   genuinely cannot be forecast, and the picker is what lets a judge ask for
 *   it.
 */
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

const CROP_FORECAST_CONFIG: Record<string, { start: number; drift: number; bandBase: number; bandSlope: number; mase: number; coverage: number }> = {
  cmd_onion: { start: 205000, drift: 1850, bandBase: 0.05, bandSlope: 0.012, mase: 0.71, coverage: 7840 },
  cmd_soyabean: { start: 438000, drift: 2400, bandBase: 0.04, bandSlope: 0.009, mase: 0.68, coverage: 8120 },
  cmd_cotton: { start: 725000, drift: 3100, bandBase: 0.045, bandSlope: 0.010, mase: 0.74, coverage: 7950 },
  cmd_tomato: { start: 124000, drift: 900, bandBase: 0.18, bandSlope: 0.022, mase: 0.98, coverage: 6120 },
  cmd_wheat: { start: 268000, drift: 1100, bandBase: 0.035, bandSlope: 0.007, mase: 0.64, coverage: 8350 },
  cmd_gram: { start: 582000, drift: 2800, bandBase: 0.042, bandSlope: 0.010, mase: 0.70, coverage: 8050 },
  cmd_maize: { start: 216000, drift: 1250, bandBase: 0.040, bandSlope: 0.008, mase: 0.69, coverage: 8100 },
};

function buildCropPoint(daysAhead: number, cfg: typeof CROP_FORECAST_CONFIG[string], level: number): ForecastPoint {
  const trend = (cfg.start + daysAhead * cfg.drift) * level;
  const slow = Math.round(2000 * Math.sin((daysAhead / 8) * Math.PI * 2) * level);
  const p50 = Math.round(trend + slow);
  const bandFraction = cfg.bandBase + daysAhead * cfg.bandSlope;
  const half = Math.round((p50 * bandFraction) / 2);
  return {
    target_date: dateNDaysAhead(daysAhead),
    p10_paise_per_qtl: p50 - half,
    p50_paise_per_qtl: p50,
    p90_paise_per_qtl: p50 + half,
  };
}

function scalePoint(p: ForecastPoint, level: number): ForecastPoint {
  return {
    target_date: p.target_date,
    p10_paise_per_qtl: Math.round(p.p10_paise_per_qtl * level),
    p50_paise_per_qtl: Math.round(p.p50_paise_per_qtl * level),
    p90_paise_per_qtl: Math.round(p.p90_paise_per_qtl * level),
  };
}

/** 14-day quantile forecast for all commodities and mandis */
export function fxForecastFor(commodityId: string, marketId: string): ForecastRes | null {
  const level = MARKET_LEVEL[marketId] ?? 1.0;

  if (commodityId === 'cmd_onion' && marketId === 'mkt_lasalgaon') {
    return fxForecast;
  }

  const cfg = CROP_FORECAST_CONFIG[commodityId] ?? CROP_FORECAST_CONFIG.cmd_onion!;

  return {
    as_of_date: dateNDaysAhead(0),
    points: Array.from({ length: 14 }, (_, i) => buildCropPoint(i + 1, cfg, level)),
    model_card: { mase: cfg.mase, coverage_80_bps: cfg.coverage },
  };
}
