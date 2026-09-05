/**
 * Mandi-Setu Voice Module — Lot Creation Parser (Track B: B4)
 * Extracts commodity, quantity (kg), and market from spoken Marathi speech.
 * Enforces rule: fields with confidence < VOICE_CONFIDENCE_THRESHOLD are left null/blank.
 */

import { VOICE_CONFIG } from './config';
import { parseQuantityKg } from './numberParser';
import { normalizeTranscriptLocally } from './textNormalizer';
import type { ParsedLotFields } from './types';

export interface ReferenceCommodity {
  id: string;
  name_mr: string;
  aliases?: string[];
}

export interface ReferenceMarket {
  id: string;
  name_mr: string;
  district_mr?: string;
  aliases?: string[];
}

export const KNOWN_COMMODITIES: ReferenceCommodity[] = [
  { id: 'onion', name_mr: 'कांदा', aliases: ['कांदे', 'कांद्याची'] },
  { id: 'soybean', name_mr: 'सोयाबीन', aliases: ['सोयाबीनचे'] },
  { id: 'tomato', name_mr: 'टोमॅटो', aliases: ['टोमॅटोचे'] },
  { id: 'maize', name_mr: 'मका', aliases: ['मक्याचे'] },
  { id: 'wheat', name_mr: 'गहू', aliases: ['गव्हाचे'] },
  { id: 'chana', name_mr: 'चना', aliases: ['हरभरा', 'चने'] },
  { id: 'cotton', name_mr: 'कापूस', aliases: ['कापसाचे'] },
];

export const KNOWN_MARKETS: ReferenceMarket[] = [
  { id: 'lasalgaon', name_mr: 'लासलगाव', district_mr: 'नाशिक' },
  { id: 'nashik', name_mr: 'नाशिक', district_mr: 'नाशिक' },
  { id: 'pimpalgaon', name_mr: 'पिंपळगाव', district_mr: 'नाशिक' },
  { id: 'baramati', name_mr: 'बारामती', district_mr: 'पुणे' },
  { id: 'pune', name_mr: 'पुणे', district_mr: 'पुणे' },
  { id: 'solapur', name_mr: 'सोलापूर', district_mr: 'सोलापूर' },
  { id: 'nagpur', name_mr: 'नागपूर', district_mr: 'नागपूर' },
  { id: 'ahmednagar', name_mr: 'अहमदनगर', district_mr: 'अहमदनगर' },
  { id: 'yeola', name_mr: 'येवला', district_mr: 'नाशिक' },
  { id: 'dindori', name_mr: 'दिंडोरी', district_mr: 'नाशिक' },
];

/**
 * Matches commodity name against known database
 */
function matchCommodity(text: string): { commodity: ReferenceCommodity | null; confidence: number } {
  for (const c of KNOWN_COMMODITIES) {
    if (text.includes(c.name_mr)) {
      return { commodity: c, confidence: 0.95 };
    }
    if (c.aliases) {
      for (const alias of c.aliases) {
        if (text.includes(alias)) {
          return { commodity: c, confidence: 0.9 };
        }
      }
    }
  }
  return { commodity: null, confidence: 0.3 };
}

/**
 * Matches mandi/market name against known database
 */
function matchMarket(text: string): { market: ReferenceMarket | null; confidence: number } {
  for (const m of KNOWN_MARKETS) {
    if (text.includes(m.name_mr)) {
      return { market: m, confidence: 0.95 };
    }
    if (m.aliases) {
      for (const alias of m.aliases) {
        if (text.includes(alias)) {
          return { market: m, confidence: 0.9 };
        }
      }
    }
  }
  return { market: null, confidence: 0.2 };
}

/**
 * Parses raw Marathi transcript into structured lot creation fields:
 * Commodity, Quantity in KG, and Mandi / Market.
 *
 * Product Rule: If confidence for any field is below threshold (0.6),
 * that field is left null rather than guessing.
 */
export function parseLotCreationSpeech(
  rawTranscript: string,
  asrConfidence = 0.9,
  threshold = VOICE_CONFIG.confidenceThreshold
): ParsedLotFields {
  if (!rawTranscript || rawTranscript.trim().length === 0) {
    return {
      commodity_id: null,
      commodity_name_mr: null,
      commodity_confidence: 0,
      qty_kg: null,
      qty_confidence: 0,
      market_id: null,
      market_name_mr: null,
      market_confidence: 0,
    };
  }

  // Normalize transcript (remove conversational fillers like "भावा", "साधारण", etc.)
  const normalized = normalizeTranscriptLocally(rawTranscript);
  const cleanedText = normalized.cleaned_text;

  // 1. Commodity Matching
  const commodityMatch = matchCommodity(cleanedText);
  const commodityConfidence = commodityMatch.confidence * asrConfidence;
  const commodityAccepted = commodityConfidence >= threshold;

  // 2. Quantity Parsing (kg)
  const qtyMatch = parseQuantityKg(cleanedText);
  const qtyConfidence = qtyMatch.confidence * asrConfidence;
  const qtyAccepted = qtyConfidence >= threshold && qtyMatch.qty_kg != null && qtyMatch.qty_kg > 0;

  // 3. Market / Mandi Matching
  const marketMatch = matchMarket(cleanedText);
  const marketConfidence = marketMatch.confidence * asrConfidence;
  const marketAccepted = marketConfidence >= threshold;

  return {
    commodity_id: commodityAccepted && commodityMatch.commodity ? commodityMatch.commodity.id : null,
    commodity_name_mr: commodityAccepted && commodityMatch.commodity ? commodityMatch.commodity.name_mr : null,
    commodity_confidence: commodityConfidence,

    qty_kg: qtyAccepted ? qtyMatch.qty_kg : null,
    qty_confidence: qtyConfidence,

    market_id: marketAccepted && marketMatch.market ? marketMatch.market.id : null,
    market_name_mr: marketAccepted && marketMatch.market ? marketMatch.market.name_mr : null,
    market_confidence: marketConfidence,
  };
}
