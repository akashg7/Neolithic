/**
 * liveMarket.ts — real market numbers for the Home (S04) and Market (PricesIndex)
 * screens.
 *
 * Those screens render a `StaticCrop` (staticMarketData.ts): presentation fields
 * (icon, photo, three-language names) plus numbers. This hook keeps the
 * presentation fields and replaces every number with `/market/overview` — the
 * latest observed mandi rate, 30-day history, the model's 14-day fan anchored on
 * that rate, the sell/hold verdict, and nearby mandis ranked by net price.
 *
 * If the server can't be reached (or has no data for that crop/mandi), the
 * static crop is returned unchanged with `live: false`, so a screen can badge it
 * instead of passing illustrative numbers off as real.
 */

import { useEffect, useState } from 'react';

import { DEFAULT_QTY_KG, USE_FIXTURES } from '../config';
import { useStaticMarket } from './staticMarketStore';
import { getMarketOverview, MarketOverview } from './api';
import { STATIC_DISTRICTS, STATIC_MANDIS, StaticCrop } from './staticMarketData';

export type LiveCrop = StaticCrop & {
  live: boolean;
  /** ISO date of the newest observation the numbers come from. */
  asOf?: string;
  /** e.g. 'ARCHIVE' — what kind of data the price is. */
  priceSource?: string;
  forecastIsModel?: boolean;
};

type Row = { label: string; price: number; min: number; max: number; arrivals: number; obs_date: string };

const rupees = (paise: number | null | undefined) => Math.round((paise ?? 0) / 100);

function toRows(points: MarketOverview['history']): Row[] {
  return points.map(p => {
    const d = new Date(`${p.obs_date}T00:00:00`);
    return {
      label: `${d.getDate()}/${d.getMonth() + 1}`,
      obs_date: p.obs_date,
      price: rupees(p.modal_paise_per_qtl),
      min: rupees(p.min_paise_per_qtl),
      max: rupees(p.max_paise_per_qtl),
      arrivals: p.arrivals_qtl,
    };
  });
}

/** Store keeps Marathi labels; the API accepts either, English is the safer match. */
export function mandiRef(selectedMandi: string): string {
  const m = STATIC_MANDIS.find(x => x.name_mr === selectedMandi || x.name === selectedMandi);
  return m ? m.name : selectedMandi;
}

export function districtRef(selectedDistrict: string): string | undefined {
  const d = STATIC_DISTRICTS.find(x => x.name_mr === selectedDistrict || x.name === selectedDistrict);
  return d ? d.name : selectedDistrict || undefined;
}

export function mergeOverview(base: StaticCrop, o: MarketOverview): LiveCrop {
  const rows = toRows(o.history);
  const hero = rupees(o.latest.modal_paise_per_qtl);
  const fc = o.forecast.points;
  const p10 = fc.map(p => p.p10_paise_per_qtl);
  const p50 = fc.map(p => p.p50_paise_per_qtl);
  const p90 = fc.map(p => p.p90_paise_per_qtl);
  const at = (i: number) => (p50.length ? rupees(p50[Math.min(i, p50.length - 1)]) : hero);
  const v = o.verdict;
  const isHold = v.action === 'HOLD' || v.action === 'SPLIT';
  const conf = v.confidence === 'HIGH' ? 'उच्च' : v.confidence === 'MEDIUM' ? 'मध्यम' : v.confidence === 'LOW' ? 'कमी' : '—';
  const rowsNearby = o.nearby.rows.map((r, i) => ({
    id: r.market_id,
    name: (r as { name?: string }).name ?? r.name_mr,
    name_mr: r.name_mr,
    name_hi: r.name_mr,
    distance_km: Math.round(r.distance_km),
    gross_paise_per_qtl: r.gross_paise_per_qtl,
    transport_paise_per_qtl: r.transport_paise_per_qtl,
    net_paise_per_qtl: r.net_paise_per_qtl,
    modal_price_per_qtl: rupees(r.gross_paise_per_qtl),
    net_price_per_qtl: rupees(r.net_paise_per_qtl),
    transport_paise: r.transport_paise_per_qtl,
    isBest: i === 0,
  }));
  const days = v.hold_days ?? 14;
  const gain = rupees(v.expected_gain_paise);

  return {
    ...base,
    live: true,
    asOf: o.latest.obs_date,
    priceSource: o.latest.source,
    forecastIsModel: o.forecast.is_model,
    heroPrice: hero,
    minPrice: rupees(o.latest.min_paise_per_qtl),
    maxPrice: rupees(o.latest.max_paise_per_qtl),
    avgPrice: rupees(o.avg_30d_paise_per_qtl),
    arrivalsQtl: o.latest.arrivals_qtl,
    arrivalsTonnes: Math.round(o.latest.arrivals_qtl / 10),
    trendDiff: rupees(o.change_7d_paise_per_qtl),
    trendPct: o.change_7d_bps != null ? Number((o.change_7d_bps / 100).toFixed(1)) : 0,
    isHold,
    confidence: conf,
    projectedDay1: at(0),
    projectedDay7: at(6),
    projectedDay14: at(13),
    projectedShift: at(13) - hero,
    holdingCost: rupees(v.itemised_costs?.storage_paise_per_qtl),
    advisoryTitleMr: v.action === 'NO_ADVICE' ? 'सल्ला देता येत नाही' : isHold ? `सल्ला: ${days} दिवस थांबा` : 'सल्ला: आजच विका',
    advisoryTitleHi: v.action === 'NO_ADVICE' ? 'सलाह संभव नहीं' : isHold ? `सलाह: ${days} दिन रुकें` : 'सलाह: आज ही बेचें',
    advisoryTitleEn: v.action === 'NO_ADVICE' ? 'No advice right now' : isHold ? `Verdict: Hold ${days} days` : 'Verdict: Sell today',
    advisorySubMr: v.explain_mr ?? '',
    advisorySubHi: v.explain_mr ?? '',
    advisorySubEn: v.explain_en ?? (isHold ? `Expected gain ₹${gain} on ${v.quantity_kg / 100} qtl.` : ''),
    history7D: rows.slice(-7),
    history14D: rows.slice(-14),
    history30D: rows.slice(-30),
    history(tf: 7 | 14 | 30 = 14) {
      return rows.slice(-tf);
    },
    forecastP10: p10,
    forecastP50: p50,
    forecastP90: p90,
    forecastFan: { p10, p50, p90 },
    nearbyMandis: rowsNearby.length ? rowsNearby : base.nearbyMandis,
  };
}

/** `crop` with live numbers once loaded; the static crop (live:false) until then or on failure. */
export function useLiveCrop(base: StaticCrop, selectedMandi: string, selectedDistrict: string) {
  const [state, setState] = useState<{ crop: LiveCrop; loading: boolean; error: string | null }>({
    crop: { ...base, live: false },
    loading: !USE_FIXTURES,
    error: null,
  });

  useEffect(() => {
    if (USE_FIXTURES) {
      setState({ crop: { ...base, live: false }, loading: false, error: null });
      return;
    }
    let cancelled = false;
    setState(s => ({ crop: { ...base, live: false }, loading: true, error: s.error }));
    getMarketOverview(base.name, mandiRef(selectedMandi), districtRef(selectedDistrict))
      .then(o => {
        if (!cancelled) setState({ crop: mergeOverview(base, o), loading: false, error: null });
      })
      .catch(e => {
        if (!cancelled) setState({ crop: { ...base, live: false }, loading: false, error: String(e?.message ?? e) });
      });
    return () => {
      cancelled = true;
    };
  }, [base, selectedMandi, selectedDistrict]);

  return state;
}

/**
 * The crop/mandi a decision screen should be about. Route params win (Home and
 * the chatbot pass exactly what they showed); otherwise the crop and mandi the
 * farmer last picked on Home/Market. The API accepts slugs or names for both.
 */
export type FocusRefs = { commodity_id: string; market_id: string; qty_kg: number };
export function useFocusRefs(params?: Partial<FocusRefs> | null): FocusRefs {
  const { selectedCrop, selectedMandi } = useStaticMarket();
  return {
    commodity_id: params?.commodity_id ?? selectedCrop.name,
    market_id: params?.market_id ?? mandiRef(selectedMandi),
    qty_kg: params?.qty_kg ?? DEFAULT_QTY_KG,
  };
}
