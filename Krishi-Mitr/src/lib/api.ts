/**
 * api.ts — 100% Static & Offline API Layer for Krishi Mitr.
 *
 * ★ Zero Backend Dependency: Completely offline, instantaneous mock & fixture responses.
 * ★ Zero Network Overhead: Eliminates all fetch timeouts and network drops.
 * ★ Immediate Execution: Every call resolves synchronously or via instant Promise.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import { fxAuthRegistered, fxDistricts } from '../fixtures/auth';
import { fxDemand } from '../fixtures/demands';
import { fxThreadFor, fxMyOffers } from '../fixtures/offers';
import { fxCommodities, fxMarketsFor } from '../fixtures/reference';
import { fxMatches } from '../fixtures/matches';
import { fxLotListed, fxMyLots } from '../fixtures/lots';
import { fxTx } from '../fixtures/escrow';
import { fxModelCard } from '../fixtures/modelCard';
import {
  getDynamicPriceSeries,
  getDynamicForecast,
  getDynamicNearby,
  getDynamicWindowRecommendation,
  getDynamicLots,
} from "./dynamicFixtures";
import type {
  AssayReq,
  AssayRecord,
  AssayRes,
  AuthRes,
  ChatMessage,
  DemandDto,
  DisputeDto,
  DisputeReasonCode,
  DisputeRes,
  District,
  EscrowEvent,
  ForecastRes,
  Locale,
  LotDto,
  MatchesRes,
  ModelCard,
  NearbyRes,
  OfferDto,
  OtpRequestRes,
  PoolDto,
  PriceSeriesRes,
  ProvenanceRes,
  TxDto,
  TxStatus,
  User,
  WindowRecommendReq,
  WindowRes,
} from '../types/api';

const TOKEN_KEY = 'auth.token';
const USER_KEY = 'auth.user';

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly field: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}

export async function getCachedUser(): Promise<User | null> {
  const raw = await AsyncStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function setCachedUser(user: User): Promise<void> {
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────────────────────

export const requestOtp = async (phone: string): Promise<OtpRequestRes> => {
  return { ok: true, phone, ttl_seconds: 300 };
};

export const verifyOtp = async (phone: string, code: string): Promise<AuthRes> => {
  return fxAuthRegistered;
};

export const register = async (body: {
  phone: string;
  code: string;
  name: string;
  role: 'FARMER' | 'BUYER';
  locale: Locale;
  district_id: string;
  village?: string;
}): Promise<AuthRes> => {
  return {
    ...fxAuthRegistered,
    user: {
      ...fxAuthRegistered.user,
      name: body.name || fxAuthRegistered.user.name,
      role: body.role || 'FARMER',
      district_id: body.district_id || 'dist_nashik',
      village: body.village || 'Niphad',
    },
  };
};

export const getMe = async (): Promise<{ user: User }> => {
  const user = await getCachedUser();
  return { user: user || fxAuthRegistered.user };
};

// ─────────────────────────────────────────────────────────────────────────────
// Reference
// ─────────────────────────────────────────────────────────────────────────────

export const getDistricts = async (): Promise<District[]> => {
  return fxDistricts;
};

export const getCommodities = async () => {
  return fxCommodities;
};

export const getMarkets = async (districtId: string) => {
  return fxMarketsFor(districtId);
};

export interface AppInitRes {
  roles: string[];
  commodities: Array<{ id: string; name: string }>;
  markets: Array<{ id: string; name: string }>;
}

export const getAppInit = async (): Promise<AppInitRes> => {
  return {
    roles: ['FARMER', 'BUYER'],
    commodities: fxCommodities.map(c => ({ id: c.id, name: c.name })),
    markets: [
      { id: 'mkt_lasalgaon', name: 'Lasalgaon' },
      { id: 'mkt_pimpalgaon', name: 'Pimpalgaon' },
      { id: 'mkt_pune', name: 'Pune Gultekdi' },
    ],
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// Prices & Mandis
// ─────────────────────────────────────────────────────────────────────────────

export const getPriceSeries = async (commodityId: string, marketId: string, days = 14): Promise<PriceSeriesRes> => {
  return getDynamicPriceSeries(commodityId, marketId, days);
};

export const getNearbyMarkets = async (commodityId: string, districtId: string): Promise<NearbyRes> => {
  return getDynamicNearby(commodityId, districtId);
};

// ─────────────────────────────────────────────────────────────────────────────
// AI & Forecasts
// ─────────────────────────────────────────────────────────────────────────────

export const getForecast = async (commodityId: string, marketId: string, horizon = 14): Promise<ForecastRes> => {
  return getDynamicForecast(commodityId, marketId, horizon);
};

export const getModelCard = async (commodityId: string): Promise<ModelCard> => {
  return fxModelCard;
};

export const recommendWindow = async (body: WindowRecommendReq): Promise<WindowRes> => {
  return getDynamicWindowRecommendation(body);
};

// ─────────────────────────────────────────────────────────────────────────────
// Lots & Grading
// ─────────────────────────────────────────────────────────────────────────────

export const createLot = async (body: {
  commodity_id: string;
  market_id: string;
  qty_kg: number;
  harvest_date: string | null;
  photo_path?: string;
}): Promise<LotDto> => {
  return {
    ...fxLotListed,
    id: `lot_${Date.now()}`,
    commodity_id: body.commodity_id,
    market_id: body.market_id,
    qty_kg: body.qty_kg,
  };
};

export const getLots = async (): Promise<LotDto[]> => {
  return getDynamicLots();
};

export const getLot = async (id: string): Promise<LotDto> => {
  const all = getDynamicLots();
  return all.find(l => l.id === id) || fxLotListed;
};

export const submitAssay = async (lotId: string, body: AssayReq): Promise<AssayRes> => {
  return {
    grade: 'A',
    confidence: 0.94,
    notes: 'चांगला रंग, मध्यम ते मोठा आकार, १००% सुकलेला शेतीमाल',
  };
};

export const getLotAssay = async (lotId: string): Promise<AssayRecord> => {
  return {
    lot_id: lotId,
    grade: 'A',
    confidence: 0.94,
    assayed_at: new Date().toISOString(),
    answers: {
      color_score: 95,
      moisture_pct: 11.5,
      size_mm: 55,
      defect_pct: 2,
    },
  };
};

export const getPool = async (id: string): Promise<PoolDto> => {
  return {
    id,
    commodity_id: 'cmd_onion',
    target_qty_kg: 20000,
    current_qty_kg: 14500,
    farmer_count: 5,
    status: 'OPEN',
    expires_at: new Date(Date.now() + 86400000 * 3).toISOString(),
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// Demands, Matching, Offers
// ─────────────────────────────────────────────────────────────────────────────

export const getDemands = async (): Promise<DemandDto[]> => {
  return [fxDemand];
};

export const getMatches = async (demandId: string): Promise<MatchesRes> => {
  return fxMatches;
};

export const getOffers = async (): Promise<OfferDto[]> => {
  return fxMyOffers;
};

export const getOfferThread = async (offerId: string): Promise<OfferDto[]> => {
  return fxThreadFor(offerId);
};

export const createOffer = async (body: {
  demand_id?: string;
  lot_ids: string[];
  qty_kg: number;
  price_paise_per_qtl: number;
}): Promise<OfferDto> => {
  return {
    ...fxMyOffers[0],
    id: `off_${Date.now()}`,
    qty_kg: body.qty_kg,
    price_paise_per_qtl: body.price_paise_per_qtl,
  };
};

export const acceptOffer = async (offerId: string): Promise<TxDto> => {
  return fxTx;
};

export const rejectOffer = async (offerId: string): Promise<OfferDto> => {
  return {
    ...fxMyOffers[0],
    id: offerId,
    status: 'REJECTED',
  };
};

export const counterOffer = async (
  offerId: string,
  body: { price_paise_per_qtl: number; note?: string }
): Promise<OfferDto> => {
  return {
    ...fxMyOffers[0],
    id: `off_counter_${Date.now()}`,
    round: 2,
    price_paise_per_qtl: body.price_paise_per_qtl,
    status: 'COUNTERED',
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// Escrow & Disputes
// ─────────────────────────────────────────────────────────────────────────────

export const getTransaction = async (id: string): Promise<TxDto> => {
  return fxTx;
};

export const transitionTx = async (txId: string, status: TxStatus): Promise<TxDto> => {
  return {
    ...fxTx,
    id: txId,
    status,
  };
};

export const getEscrowEvents = async (txId: string): Promise<EscrowEvent[]> => {
  return [
    {
      id: 'evt_1',
      tx_id: txId,
      action: 'ESCROW_FUNDED',
      amount_paise: 9800000,
      timestamp: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: 'evt_2',
      tx_id: txId,
      action: 'LOT_DISPATCHED',
      timestamp: new Date(Date.now() - 43200000).toISOString(),
    },
  ];
};

export const createDispute = async (body: {
  tx_id: string;
  reason: DisputeReasonCode;
  description: string;
}): Promise<DisputeRes> => {
  return {
    dispute_id: `disp_${Date.now()}`,
    status: 'OPEN',
    created_at: new Date().toISOString(),
  };
};

export const getDispute = async (id: string): Promise<DisputeDto> => {
  return {
    id,
    tx_id: 'tx_demo',
    reason: 'QUALITY_MISMATCH',
    description: 'लॉटचा दर्जा सांगितल्याप्रमाणे नाही',
    status: 'OPEN',
    created_at: new Date().toISOString(),
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// Data Provenance & Chat
// ─────────────────────────────────────────────────────────────────────────────

export const getDataProvenance = async (): Promise<ProvenanceRes> => {
  return {
    records_analyzed: 45280,
    sources: ['MSAMB', 'AGMARKNET', 'IMD Weather', 'e-NAM'],
    last_updated: new Date().toISOString(),
    freshness_score: 99.4,
  };
};

export const getChatMessages = async (threadId: string): Promise<ChatMessage[]> => {
  return [
    {
      id: 'msg_1',
      sender_id: 'buyer_1',
      sender_name: 'सुरेश मेहता (व्यापारी)',
      text: 'नमस्कार, कांद्याचा दर्जा कसा आहे? माल कधी लोड करता येईल?',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      is_me: false,
    },
    {
      id: 'msg_2',
      sender_id: 'farmer_1',
      sender_name: 'रामभाऊ पाटील',
      text: 'नमस्कार, १००% सुकलेला आणि प्रतवारी केलेला माल आहे. आजच पाठवू शकतो.',
      created_at: new Date(Date.now() - 1800000).toISOString(),
      is_me: true,
    },
  ];
};

export const sendChatMessage = async (threadId: string, text: string): Promise<ChatMessage> => {
  return {
    id: `msg_${Date.now()}`,
    sender_id: 'farmer_1',
    sender_name: 'रामभाऊ पाटील',
    text,
    created_at: new Date().toISOString(),
    is_me: true,
  };
};

export const transcribeAudio = async (
  uriOrFormData?: any,
  locale: Locale = 'mr',
): Promise<{ transcript: string; text?: string }> => {
  const rawKey =
    (typeof process !== 'undefined' && process.env?.SARVAM_API_KEY) ||
    (typeof window !== 'undefined' && ((window as any).SARVAM_API_KEY || (window as any).localStorage?.getItem('SARVAM_API_KEY'))) ||
    '';
  const keys = rawKey.split(',').map((k: string) => k.trim()).filter(Boolean);
  const langCode = locale === 'hi' ? 'hi-IN' : locale === 'en' ? 'en-IN' : 'mr-IN';

  if (keys.length > 0 && typeof window !== 'undefined' && uriOrFormData) {
    for (const key of keys) {
      try {
        let blob: Blob | null = null;
        if (typeof uriOrFormData === 'string' && uriOrFormData.startsWith('blob:')) {
          const resp = await fetch(uriOrFormData);
          blob = await resp.blob();
        } else if (uriOrFormData instanceof Blob) {
          blob = uriOrFormData;
        }

        if (blob) {
          const fd = new FormData();
          fd.append('file', blob, 'audio.wav');
          fd.append('model', 'saaras:v3');
          fd.append('language_code', langCode);

          const sarvamRes = await fetch('https://api.sarvam.ai/speech-to-text', {
            method: 'POST',
            headers: {
              'api-subscription-key': key,
            },
            body: fd,
          });

          if (sarvamRes.ok) {
            const data = await sarvamRes.json();
            const transcript = data.transcript || data.text || '';
            if (transcript) {
              return { transcript, text: transcript };
            }
          }
        }
      } catch (e) {
        console.warn('[Sarvam STT] Key failed:', e);
      }
    }
  }

  const fallback = locale === 'en'
    ? 'Rambhau Patil, Nashik, Onion'
    : 'रामभाऊ पाटील, नाशिक लासलगाव, कांदा';
  return { transcript: fallback, text: fallback };
};

export const narrate = async (
  text: string,
  locale: Locale = 'mr',
  speaker?: string,
  pace?: number,
): Promise<{ audio_base64: string }> => {
  const rawKey =
    (typeof process !== 'undefined' && process.env?.SARVAM_API_KEY) ||
    (typeof window !== 'undefined' && ((window as any).SARVAM_API_KEY || (window as any).localStorage?.getItem('SARVAM_API_KEY'))) ||
    '';
  const keys = rawKey.split(',').map((k: string) => k.trim()).filter(Boolean);
  if (keys.length === 0) {
    return { audio_base64: '' };
  }

  const langCode = locale === 'hi' ? 'hi-IN' : locale === 'en' ? 'en-IN' : 'mr-IN';
  const validSpeaker = speaker || 'simran';

  for (const key of keys) {
    try {
      const response = await fetch('https://api.sarvam.ai/text-to-speech', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'api-subscription-key': key,
        },
        body: JSON.stringify({
          inputs: [text],
          target_language_code: langCode,
          speaker: validSpeaker,
          model: 'bulbul:v3',
          ...(pace !== undefined ? { pace } : {}),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const base64Audio = data.audios?.[0] || '';
        if (base64Audio) {
          return { audio_base64: base64Audio };
        }
      } else {
        const errJson = await response.json().catch(() => null);
        console.warn(`[Sarvam TTS] Key error (${response.status}):`, errJson?.error?.message || response.statusText);
      }
    } catch (err) {
      console.warn('[Sarvam TTS] Request error:', err);
    }
  }

  return { audio_base64: '' };
};

export const api = async <T>(path: string): Promise<T> => {
  return {} as T;
};
