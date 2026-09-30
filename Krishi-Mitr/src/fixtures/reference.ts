/**
 * CANON §7.2-shaped fixtures for `GET /ref/commodities` and
 * `GET /ref/markets?district_id=`. Kartik's K5 does not exist yet.
 *
 * ★ There are two commodities, and that is not a placeholder — it is the
 *   scope. `docs/roles/KARTIK.md` §"Commodities": *"2 — onion + tomato.
 *   Tomato is the NO_ADVICE crop. One commodity cannot demonstrate refusal."*
 *   The crop picker on the market screen therefore offers two crops, not a
 *   long menu of vegetables. A dropdown listing twenty crops the model has
 *   never seen would be a list of promises the forecast cannot keep, and the
 *   farmer would find that out only after asking one of them.
 *
 * ★ Markets are per district because a district does not identify a price
 *   series — `/prices/series` is keyed by mandi. Nashik has two, so the
 *   picker has something real to disambiguate rather than a single option
 *   dressed up as a choice.
 *
 * ★ `storable_days` and `spoilage` are why the two crops behave differently
 *   downstream: onion keeps for months and can be held, tomato cannot. The
 *   decision engine reads that, and it is the reason waiting is a real option
 *   for one crop and not the other.
 */

import type { Commodity, Market } from '../types/api';

export const fxCommodities: Commodity[] = [
  { id: 'cmd_onion', name: 'Onion (कांदा)', name_mr: 'कांदा', storable_days: 150 },
  { id: 'cmd_soyabean', name: 'Soyabean (सोयाबीन)', name_mr: 'सोयाबीन', storable_days: 180 },
  { id: 'cmd_cotton', name: 'Cotton (कापूस)', name_mr: 'कापूस', storable_days: 210 },
  { id: 'cmd_tomato', name: 'Tomato (टोमॅटो)', name_mr: 'टोमॅटो', storable_days: 7 },
  { id: 'cmd_wheat', name: 'Wheat (गहू)', name_mr: 'गहू', storable_days: 360 },
  { id: 'cmd_gram', name: 'Gram / Chana (हरभरा)', name_mr: 'हरभरा', storable_days: 240 },
  { id: 'cmd_maize', name: 'Maize (मका)', name_mr: 'मका', storable_days: 180 },
];

/**
 * Keyed by district across Maharashtra's premier agricultural trading hubs.
 */
export const fxMarketsByDistrict: Record<string, Market[]> = {
  dist_nashik: [
    {
      id: 'mkt_lasalgaon',
      name: 'Lasalgaon',
      name_mr: 'लासलगाव',
      district_id: 'dist_nashik',
      lat: 20.1428,
      lon: 74.2394,
    },
    {
      id: 'mkt_pimpalgaon',
      name: 'Pimpalgaon Baswant',
      name_mr: 'पिंपळगाव बसवंत',
      district_id: 'dist_nashik',
      lat: 20.1697,
      lon: 73.9819,
    },
    {
      id: 'mkt_yeola',
      name: 'Yeola',
      name_mr: 'येवला',
      district_id: 'dist_nashik',
      lat: 20.0421,
      lon: 74.4842,
    },
  ],
  dist_latur: [
    {
      id: 'mkt_latur',
      name: 'Latur APMC',
      name_mr: 'लातूर मुख्य बाजार',
      district_id: 'dist_latur',
      lat: 18.4088,
      lon: 76.5604,
    },
    {
      id: 'mkt_udgir',
      name: 'Udgir',
      name_mr: 'उदगीर',
      district_id: 'dist_latur',
      lat: 18.3942,
      lon: 77.1187,
    },
  ],
  dist_ahmednagar: [
    {
      id: 'mkt_ahmednagar',
      name: 'Ahmednagar',
      name_mr: 'अहमदनगर',
      district_id: 'dist_ahmednagar',
      lat: 19.0948,
      lon: 74.748,
    },
    {
      id: 'mkt_kopargaon',
      name: 'Kopargaon',
      name_mr: 'कोपरगाव',
      district_id: 'dist_ahmednagar',
      lat: 19.8912,
      lon: 74.4789,
    },
    {
      id: 'mkt_rahata',
      name: 'Rahata',
      name_mr: 'राहाता',
      district_id: 'dist_ahmednagar',
      lat: 19.7042,
      lon: 74.4984,
    },
  ],
  dist_pune: [
    {
      id: 'mkt_pune',
      name: 'Pune Gultekdi',
      name_mr: 'पुणे गुलटेकडी',
      district_id: 'dist_pune',
      lat: 18.5204,
      lon: 73.8567,
    },
    {
      id: 'mkt_junnar',
      name: 'Junnar (Narayangaon)',
      name_mr: 'जुन्नर (नारायणगाव)',
      district_id: 'dist_pune',
      lat: 19.1215,
      lon: 73.9782,
    },
    {
      id: 'mkt_baramati',
      name: 'Baramati',
      name_mr: 'बारामती',
      district_id: 'dist_pune',
      lat: 18.1517,
      lon: 74.5772,
    },
  ],
  dist_jalgaon: [
    {
      id: 'mkt_jalgaon',
      name: 'Jalgaon',
      name_mr: 'जळगाव',
      district_id: 'dist_jalgaon',
      lat: 21.0077,
      lon: 75.5626,
    },
    {
      id: 'mkt_chalisgaon',
      name: 'Chalisgaon',
      name_mr: 'चाळीसगाव',
      district_id: 'dist_jalgaon',
      lat: 20.4636,
      lon: 74.9964,
    },
  ],
  dist_solapur: [
    {
      id: 'mkt_solapur',
      name: 'Solapur APMC',
      name_mr: 'सोलापूर बाजार समिती',
      district_id: 'dist_solapur',
      lat: 17.6599,
      lon: 75.9064,
    },
    {
      id: 'mkt_pandharpur',
      name: 'Pandharpur',
      name_mr: 'पंढरपूर',
      district_id: 'dist_solapur',
      lat: 17.6776,
      lon: 75.3284,
    },
  ],
  dist_aurangabad: [
    {
      id: 'mkt_aurangabad',
      name: 'Chhatrapati Sambhajinagar',
      name_mr: 'छत्रपती संभाजीनगर (जाधववाडी)',
      district_id: 'dist_aurangabad',
      lat: 19.8762,
      lon: 75.3433,
    },
    {
      id: 'mkt_vaijapur',
      name: 'Vaijapur',
      name_mr: 'वैजापूर',
      district_id: 'dist_aurangabad',
      lat: 19.9272,
      lon: 74.7289,
    },
  ],
  dist_yavatmal: [
    {
      id: 'mkt_yavatmal',
      name: 'Yavatmal APMC',
      name_mr: 'यवतमाळ बाजार समिती',
      district_id: 'dist_yavatmal',
      lat: 20.3888,
      lon: 78.1204,
    },
    {
      id: 'mkt_wani',
      name: 'Wani',
      name_mr: 'वणी',
      district_id: 'dist_yavatmal',
      lat: 20.0617,
      lon: 78.9515,
    },
  ],
};

export function fxMarketsFor(districtId: string): Market[] {
  return fxMarketsByDistrict[districtId] ?? [];
}
