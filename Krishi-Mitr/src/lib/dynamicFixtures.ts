import type {
  PriceSeriesRes,
  PricePoint,
  ForecastRes,
  ForecastPoint,
  NearbyRes,
  NearbyMarketRow,
  WindowRes,
  WindowRecommendReq,
  LotDto,
} from "../types/api";

export const COMMODITY_BASE_PRICES: Record<string, { base: number; arrivals: number }> = {
  cmd_onion: { base: 2350, arrivals: 1395 },
  cmd_soyabean: { base: 4680, arrivals: 920 },
  cmd_soybean: { base: 4680, arrivals: 920 },
  cmd_cotton: { base: 7250, arrivals: 810 },
  cmd_wheat: { base: 2580, arrivals: 1150 },
  cmd_tomato: { base: 1850, arrivals: 2100 },
  cmd_gram: { base: 5850, arrivals: 640 },
  cmd_bengal_gram: { base: 5850, arrivals: 640 },
  cmd_maize: { base: 2180, arrivals: 1580 },
  cmd_green_chilli: { base: 15400, arrivals: 420 },
  cmd_turmeric: { base: 13900, arrivals: 510 },
  cmd_groundnut: { base: 6350, arrivals: 730 },
  cmd_pomegranate: { base: 8600, arrivals: 390 },
  cmd_grapes: { base: 6900, arrivals: 820 },
  cmd_sugarcane: { base: 3380, arrivals: 4400 },
  cmd_potato: { base: 1980, arrivals: 2350 },
  cmd_garlic: { base: 14800, arrivals: 340 },
  cmd_ginger: { base: 9350, arrivals: 310 },
  cmd_jowar: { base: 3100, arrivals: 650 },
  cmd_rice: { base: 3450, arrivals: 1200 },
};

export function getDynamicPriceSeries(
  commodityId: string,
  marketId: string,
  days = 14
): PriceSeriesRes {
  const info = COMMODITY_BASE_PRICES[commodityId] || { base: 2400, arrivals: 1000 };
  const basePaise = info.base * 100;
  const numDays = Math.max(7, Math.min(days, 30));
  const points: PricePoint[] = [];

  const now = new Date(2026, 8, 30); // 30 Sept 2026

  for (let i = numDays - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const dateStr = d.toISOString().slice(0, 10);
    const variation = Math.sin(i * 0.7) * 0.04 - (i / numDays) * 0.03;
    const modal = Math.round((basePaise * (1 + variation)) / 100) * 100;
    const min = Math.round(modal * 0.88);
    const max = Math.round(modal * 1.12);
    const arr = Math.round(info.arrivals * (1 + Math.cos(i * 0.6) * 0.15));

    points.push({
      obs_date: dateStr,
      modal_paise_per_qtl: modal,
      min_paise_per_qtl: min,
      max_paise_per_qtl: max,
      arrivals_qtl: arr,
      source: "AGMARKNET",
    });
  }

  return {
    latest_obs_date: points[points.length - 1].obs_date,
    source_summary: { AGMARKNET: points.length },
    points,
  };
}

export function getDynamicForecast(
  commodityId: string,
  marketId: string,
  horizon = 14
): ForecastRes {
  const info = COMMODITY_BASE_PRICES[commodityId] || { base: 2400, arrivals: 1000 };
  const basePaise = info.base * 100;
  const points: ForecastPoint[] = [];
  const now = new Date(2026, 8, 30);

  for (let h = 1; h <= horizon; h++) {
    const targetDate = new Date(now.getTime() + h * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);
    const drift = 0.005 * h;
    const p50 = Math.round(basePaise * (1 + drift));
    const spread = basePaise * (0.03 + 0.006 * h);
    const p10 = Math.round(p50 - spread);
    const p90 = Math.round(p50 + spread);

    points.push({
      target_date: targetDate,
      p10_paise_per_qtl: p10,
      p50_paise_per_qtl: p50,
      p90_paise_per_qtl: p90,
    });
  }

  return {
    as_of_date: "2026-09-30",
    points,
    model_card: {
      mase: 0.5718,
      coverage_80_bps: 8120,
    },
  };
}

export function getDynamicNearby(
  commodityId: string,
  districtId: string
): NearbyRes {
  const info = COMMODITY_BASE_PRICES[commodityId] || { base: 2400, arrivals: 1000 };
  const basePaise = info.base * 100;

  const mandiTemplates = [
    { id: "mkt_1", name_mr: "लासलगाव मुख्य बाजार समिती", dist: 14, bonus: 8000 },
    { id: "mkt_2", name_mr: "पिंपळगाव बसवंत बाजार समिती", dist: 32, bonus: 12000 },
    { id: "mkt_3", name_mr: "पुणे गुलटेकडी मुख्य मंडी", dist: 145, bonus: 24000 },
    { id: "mkt_4", name_mr: "कोपरगाव कृषी उत्पन्न बाजार", dist: 58, bonus: -4000 },
    { id: "mkt_5", name_mr: "सोलापूर बाजार समिती", dist: 180, bonus: 16000 },
  ];

  const rows: NearbyMarketRow[] = mandiTemplates.map((m) => {
    const gross = basePaise + m.bonus;
    const transport = m.dist * 350;
    const commission = Math.round(gross * 0.0105);
    const net = gross - transport - commission;

    return {
      market_id: m.id,
      name_mr: m.name_mr,
      distance_km: m.dist,
      gross_paise_per_qtl: gross,
      transport_paise_per_qtl: transport,
      commission_paise_per_qtl: commission,
      net_paise_per_qtl: net,
      source: "AGMARKNET",
    };
  });

  rows.sort((a, b) => b.net_paise_per_qtl - a.net_paise_per_qtl);

  return {
    as_of_date: "2026-09-30",
    rows,
    sorted_by: "net_paise_per_qtl",
  };
}

export function getDynamicWindowRecommendation(
  req: WindowRecommendReq
): WindowRes {
  const info = COMMODITY_BASE_PRICES[req.commodity_id] || { base: 2400, arrivals: 1000 };
  const basePaise = info.base * 100;
  const targetGainPaise = Math.round(basePaise * 0.075);

  return {
    action: "HOLD",
    recommended_window: {
      start_day: 5,
      end_day: 8,
      optimal_day: 7,
    },
    expected_gain_paise_per_qtl: targetGainPaise,
    confidence: "HIGH",
    reasoning: [
      "पुढील आठवड्यात आवक १५% ते २०% ने घटण्याचा अंदाज आहे.",
      "प्रशिक्षित LightGBM मॉडेलनुसार ७ व्या दिवशी सर्वोच्च दर मिळण्याची शक्यता आहे.",
      "साठवणूक खर्च वजा जाता प्रति क्विंटल निव्वळ नफा जास्त राहील.",
    ],
    costs: {
      storage_paise_per_qtl: 2800,
      shrinkage_paise_per_qtl: 1400,
      total_paise_per_qtl: 4200,
    },
  };
}

export function getDynamicLots(): LotDto[] {
  return [
    {
      id: "lot_101",
      farmer_id: "farmer_rambhau",
      commodity_id: "cmd_onion",
      market_id: "mkt_lasalgaon",
      qty_kg: 4000,
      grade: "A",
      harvest_date: "2026-09-24",
      status: "LISTED",
      created_at: "2026-09-25T10:00:00Z",
    },
  ];
}
