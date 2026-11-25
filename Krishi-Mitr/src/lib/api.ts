/**
 * api.ts — the app's only door to the FastAPI backend (`API_BASE_URL`, /api/v1).
 *
 * ★ Every function talks to the real server: JWT attached, the backend's error
 *   envelope `{error:{code,message,field}}` turned into `ApiError`, a timeout on
 *   every call. Responses are read in the app's wire contract (`types/api.ts`);
 *   the few places where the backend's shape differs are mapped here, once, so
 *   screens never see the difference.
 *
 * ★ `USE_FIXTURES` (config.ts) is the demo-day fallback ladder's last rung: when
 *   true, the fixture responses below are returned instead and nothing touches
 *   the network. It is false in normal use.
 *
 * ★ Two features have no backend yet and stay on fixtures in every mode, said
 *   plainly at the call site: FPO pool split (`getPool`) and buyer↔farmer chat
 *   (`getChatMessages`/`sendChatMessage`).
 *
 * ★ No API keys live in the app. Voice goes through `/voice/*` on our server,
 *   which holds the Sarvam key.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import { API_BASE_URL, USE_FIXTURES } from '../config';
import { fxAuthRegistered, fxAuthRegisteredBuyer, fxDistricts } from '../fixtures/auth';
import { fxDemand } from '../fixtures/demands';
import { fxThreadFor, fxMyOffers } from '../fixtures/offers';
import { fxCommodities, fxMarketsFor } from '../fixtures/reference';
import { fxMatches } from '../fixtures/matches';
import { fxLotListed } from '../fixtures/lots';
import { fxTx } from '../fixtures/escrow';
import { fxModelCard } from '../fixtures/modelCard';
import {
  getDynamicPriceSeries,
  getDynamicForecast,
  getDynamicNearby,
  getDynamicWindowRecommendation,
  getDynamicLots,
} from './dynamicFixtures';
import type {
  AssayReq,
  AssayRecord,
  AssayRes,
  AuthRes,
  Commodity,
  DemandDto,
  DisputeDto,
  DisputeReasonCode,
  DisputeRes,
  District,
  EscrowEvent,
  ForecastRes,
  Locale,
  LotDto,
  LotStatus,
  Market,
  MatchesRes,
  ModelCard,
  NearbyRes,
  OfferDto,
  OtpRequestRes,
  PoolDto,
  PriceSeriesRes,
  ProvenanceRes,
  Role,
  TxDto,
  TxStatus,
  User,
  WindowRecommendReq,
  WindowRes,
} from '../types/api';

/** One chat bubble (S27/S37). Not in the CANON contract — messaging has no backend yet. */
export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  text: string;
  created_at: string;
  is_me: boolean;
}

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
// HTTP core
// ─────────────────────────────────────────────────────────────────────────────

type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOpts {
  query?: Query;
  body?: unknown;
  form?: FormData;
  /** Milliseconds. Voice and AI get longer budgets than reads. */
  timeoutMs?: number;
}

/** Called once per 401 so the auth layer can sign the user out (see auth.tsx). */
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn;
}

function withQuery(path: string, query?: Query): string {
  if (!query) return path;
  const qs = Object.entries(query)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  return qs ? `${path}?${qs}` : path;
}

async function request<T>(method: string, path: string, opts: RequestOpts = {}): Promise<T> {
  const url = `${API_BASE_URL}${withQuery(path, opts.query)}`;
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = await getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form as unknown as BodyInit; // fetch sets the multipart boundary
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 15000);
  let res: Response;
  try {
    res = await fetch(url, { method, headers, body, signal: controller.signal });
  } catch (e) {
    const aborted = (e as { name?: string })?.name === 'AbortError';
    throw new ApiError(
      aborted ? 'TIMEOUT' : 'NETWORK',
      aborted ? 'The server took too long to respond.' : 'Could not reach the server.',
      0,
    );
  } finally {
    clearTimeout(timer);
  }

  const text = await res.text();
  let data: any = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const env = data?.error ?? data?.detail?.error;
    const code: string = env?.code ?? (res.status === 401 ? 'UNAUTHENTICATED' : `HTTP_${res.status}`);
    const message: string =
      (typeof env?.message === 'string' && env.message) ||
      (typeof data?.detail === 'string' && data.detail) ||
      res.statusText ||
      'Request failed';
    if (res.status === 401 && token && onUnauthorized) onUnauthorized();
    throw new ApiError(code, message, res.status, env?.field ?? null);
  }
  return data as T;
}

const get = <T>(path: string, query?: Query, timeoutMs?: number) =>
  request<T>('GET', path, { query, timeoutMs });
const post = <T>(path: string, body?: unknown, timeoutMs?: number) =>
  request<T>('POST', path, { body: body ?? {}, timeoutMs });

/** Generic GET, for the odd screen that needs an endpoint without a helper. */
export const api = async <T>(path: string, query?: Query): Promise<T> => get<T>(path, query);

// ─────────────────────────────────────────────────────────────────────────────
// Shape mappers — the only place backend and app contracts are reconciled
// ─────────────────────────────────────────────────────────────────────────────

/** Backend lot statuses → the app's `LotStatus`. */
function lotStatus(s: string): LotStatus {
  switch ((s || '').toUpperCase()) {
    case 'DRAFT': return 'DRAFT';
    case 'OFFERED': return 'OFFERED';
    case 'POOLED': return 'POOLED';
    case 'CANCELLED': return 'CANCELLED';
    case 'SOLD': return 'COMMITTED';
    case 'COMPLETED': return 'SETTLED';
    default: return 'LISTED';
  }
}

function toLot(l: any): LotDto {
  return {
    id: String(l.id),
    farmer_id: String(l.farmer_id),
    commodity_id: l.commodity_id,
    market_id: l.market_id ?? '',
    qty_kg: l.qty_kg,
    grade: l.grade ?? 'UNGRADED',
    harvest_date: l.harvest_date ?? null,
    photo_path: l.photo_path ?? null,
    status: lotStatus(l.status),
    created_at: l.created_at ?? new Date().toISOString(),
    // Not in the CANON contract, but the server sends it and S22/S24 can use it.
    ...(l.expected_price_paise != null ? { expected_price_paise: l.expected_price_paise } : {}),
  } as LotDto;
}

/** The escrow FSM's state names (several aliases each) → the app's `TxStatus`. */
function txStatus(s: string | null | undefined): TxStatus {
  switch ((s || '').toUpperCase()) {
    case 'DEPOSIT_HELD':
    case 'ESCROW_HELD':
      return 'ESCROW_HELD';
    case 'IN_TRANSIT':
    case 'DISPATCHED':
    case 'ARRIVED_PENDING_INSPECTION':
      return 'DISPATCHED';
    case 'INSPECTED':
    case 'INSPECTION_PASSED':
    case 'DELIVERED':
      return 'DELIVERED';
    case 'FUNDS_RELEASED':
    case 'RELEASED':
      return 'RELEASED';
    case 'DISPUTED':
    case 'DISPUTED_QUALITY':
    case 'DISPUTED_NO_SHOW':
      return 'DISPUTED';
    case 'REFUNDED':
      return 'REFUNDED';
    case 'CANCELLED':
      return 'CANCELLED';
    default:
      return 'CREATED';
  }
}

/** Transaction + (if known) its offer → `TxDto`. Qty and price come from the offer. */
function toTx(t: any, offer?: OfferDto): TxDto {
  const gross: number = t.amount_paise ?? t.total_amount_paise ?? 0;
  const qty = offer?.qty_kg ?? 0;
  const price = offer?.price_paise_per_qtl ?? (qty ? Math.round(gross / (qty / 100)) : 0);
  return {
    id: String(t.id),
    offer_id: String(t.offer_id),
    buyer_id: String(t.buyer_id ?? offer?.buyer_id ?? ''),
    farmer_id: t.farmer_id != null ? String(t.farmer_id) : offer?.farmer_id ?? null,
    pool_id: null,
    qty_kg: qty,
    price_paise_per_qtl: price,
    gross_paise: gross,
    // Platform deductions aren't modelled server-side yet: the farmer receives the gross.
    deductions_paise: 0,
    net_paise: gross,
    status: txStatus(t.status),
    created_at: t.created_at ?? new Date().toISOString(),
  };
}

function toEvent(e: any): EscrowEvent {
  return {
    id: String(e.id),
    tx_id: String(e.transaction_id),
    from_status: e.status_from || e.from_state ? txStatus(e.status_from || e.from_state) : null,
    to_status: txStatus(e.status_to || e.to_state),
    actor_user_id: e.actor_id != null ? String(e.actor_id) : null,
    note: e.note ?? null,
    created_at: e.created_at ?? new Date().toISOString(),
  };
}

const DISPUTE_CODES: DisputeReasonCode[] = ['QUALITY_MISMATCH', 'SHORT_WEIGHT', 'PAYMENT_DELAY', 'OTHER'];

function toDispute(d: any): DisputeDto {
  // The server stores "CODE: description" in one `reason` column.
  const raw: string = d.reason ?? '';
  const [maybeCode = '', ...rest] = raw.split(': ');
  const code = (DISPUTE_CODES as string[]).includes(maybeCode) ? (maybeCode as DisputeReasonCode) : 'OTHER';
  const stage =
    d.status === 'resolved' ? 'RESOLVED_SPLIT' : d.status === 'dismissed' ? 'WITHDRAWN'
      : d.status === 'investigating' || d.status === 'under_review' ? 'MEDIATION' : 'RAISED';
  return {
    id: String(d.id),
    tx_id: String(d.transaction_id),
    raised_by: String(d.raised_by ?? d.raised_by_id ?? ''),
    reason_code: code,
    description: code === 'OTHER' && rest.length === 0 ? raw : rest.join(': ') || null,
    photo_path: null,
    stage,
    created_at: d.created_at ?? new Date().toISOString(),
  };
}

function toDemand(d: any): DemandDto {
  return {
    id: String(d.id),
    buyer_id: String(d.buyer_id ?? ''),
    commodity_id: d.commodity_id,
    market_id: d.market_id ?? '',
    qty_kg: (d.quantity_qtl ?? 0) * 100,
    min_grade: (d.desired_grade as DemandDto['min_grade']) || 'C',
    bid_paise_per_qtl: d.expected_price_paise ?? 0,
    needed_by: d.needed_by ?? '',
    status: (d.status || '').toLowerCase() === 'active' ? 'OPEN' : ((d.status || 'OPEN').toUpperCase() as DemandDto['status']),
    source: d.source === 'demo' ? 'SEEDED' : 'REAL',
    created_at: d.created_at ?? '',
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────────────────────

/**
 * There is no SMS provider yet. Outside production the server returns the code
 * it just generated as `dev_otp`; the OTP screen shows it so a tester can sign
 * in. Every code is random, single-phone, expires, and is attempt-capped
 * server-side; production never returns it.
 */
let lastDevOtp: { phone: string; code: string } | null = null;
export const getDevOtp = (phone: string): string | null =>
  lastDevOtp && lastDevOtp.phone === phone ? lastDevOtp.code : null;

export const requestOtp = async (phone: string): Promise<OtpRequestRes> => {
  if (USE_FIXTURES) return { ok: true, expires_in_s: 300, dev_otp: '123456' };
  const res = await post<OtpRequestRes>('/auth/otp/request', { phone });
  lastDevOtp = res.dev_otp ? { phone, code: res.dev_otp } : null;
  return res;
};

export const verifyOtp = async (phone: string, code: string): Promise<AuthRes> => {
  if (USE_FIXTURES) return fxAuthRegistered;
  return post<AuthRes>('/auth/otp/verify', { phone, code });
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
  if (USE_FIXTURES) {
    return {
      ...fxAuthRegistered,
      user: { ...fxAuthRegistered.user, name: body.name, role: body.role, district_id: body.district_id },
    };
  }
  return post<AuthRes>('/auth/register', body);
};

/** One-tap sign-in as the seeded demo farmer/buyer (server must run with DEMO_MODE=true). */
export const demoLogin = async (role: Role = 'FARMER'): Promise<AuthRes> => {
  if (USE_FIXTURES) return role === 'BUYER' ? fxAuthRegisteredBuyer : fxAuthRegistered;
  return post<AuthRes>('/auth/demo-login', { role });
};

/** "Go to dashboard" shortcuts: reuse a real saved session, else the server's demo login. */
export const enterDashboard = async (role: Role = 'FARMER'): Promise<AuthRes> => {
  const [token, user] = await Promise.all([getToken(), getCachedUser()]);
  if (token && user && !token.startsWith('fixture-')) return { token, user };
  return demoLogin(role);
};

export const getMe = async (): Promise<{ user: User }> => {
  if (USE_FIXTURES) {
    const user = await getCachedUser();
    return { user: user || fxAuthRegistered.user };
  }
  return get<{ user: User }>('/auth/me');
};

export const updateLocale = async (locale: Locale): Promise<void> => {
  if (USE_FIXTURES) return;
  await post('/auth/locale', { locale });
};

// ─────────────────────────────────────────────────────────────────────────────
// Reference
// ─────────────────────────────────────────────────────────────────────────────

export const getDistricts = async (): Promise<District[]> => {
  if (USE_FIXTURES) return fxDistricts;
  return get<District[]>('/ref/districts');
};

export const getCommodities = async (): Promise<Commodity[]> => {
  if (USE_FIXTURES) return fxCommodities;
  return get<Commodity[]>('/ref/commodities');
};

/** Every mandi the server knows (all districts). */
export const getAllMarkets = async (): Promise<Market[]> => {
  if (USE_FIXTURES) return [];
  return get<Market[]>('/ref/markets');
};

export const getMarkets = async (districtId: string): Promise<Market[]> => {
  if (USE_FIXTURES) return fxMarketsFor(districtId);
  return get<Market[]>('/ref/markets', { district_id: districtId });
};

export interface AppInitRes {
  roles: string[];
  commodities: Array<{ id: string; name: string }>;
  markets: Array<{ id: string; name: string }>;
}

export const getAppInit = async (): Promise<AppInitRes> => {
  if (USE_FIXTURES) {
    return {
      roles: ['FARMER', 'BUYER'],
      commodities: fxCommodities.map(c => ({ id: c.id, name: c.name })),
      markets: [{ id: 'mkt_lasalgaon', name: 'Lasalgaon' }],
    };
  }
  return get<AppInitRes>('/meta/init');
};

// Name lookup for any reference slug the app's i18n tables don't cover. Filled
// once from /ref (public, cached); screens read it synchronously via refLabel().
const refNames: Record<string, { name: string; name_mr: string }> = {};
let refNamesLoad: Promise<void> | null = null;

export function loadRefNames(): Promise<void> {
  if (USE_FIXTURES) return Promise.resolve();
  if (!refNamesLoad) {
    refNamesLoad = Promise.all([
      get<Commodity[]>('/ref/commodities'),
      get<Market[]>('/ref/markets'),
      get<District[]>('/ref/districts'),
    ])
      .then(([cs, ms, ds]) => {
        for (const r of [...cs, ...ms, ...ds]) refNames[r.id] = { name: r.name, name_mr: r.name_mr };
      })
      .catch(() => {
        refNamesLoad = null; // retry next time
      });
  }
  return refNamesLoad;
}

/** Human name for a slug (`cmd_onion` → "कांदा"/"Onion"); the slug itself if unknown. */
export function refLabel(id: string | null | undefined, locale: Locale): string {
  if (!id) return '';
  const r = refNames[id];
  if (!r) return id;
  return locale === 'en' ? r.name : r.name_mr || r.name;
}

// ─────────────────────────────────────────────────────────────────────────────
// Prices & Mandis
// ─────────────────────────────────────────────────────────────────────────────

export const getPriceSeries = async (commodityId: string, marketId: string, days = 14): Promise<PriceSeriesRes> => {
  if (USE_FIXTURES) return getDynamicPriceSeries(commodityId, marketId, days);
  return get<PriceSeriesRes>('/prices/series', { commodity_id: commodityId, market_id: marketId, days });
};

export const getNearbyMarkets = async (commodityId: string, districtId: string): Promise<NearbyRes> => {
  if (USE_FIXTURES) return getDynamicNearby(commodityId, districtId);
  return get<NearbyRes>('/prices/nearby', { commodity_id: commodityId, district_id: districtId });
};

/** Everything S04/PricesIndex show for one crop at one mandi (see lib/liveMarket.ts). */
export interface MarketOverview {
  commodity: { slug: string; name: string; name_mr: string };
  market: { slug: string; name: string; name_mr: string };
  latest: {
    obs_date: string;
    min_paise_per_qtl: number;
    max_paise_per_qtl: number;
    modal_paise_per_qtl: number;
    arrivals_qtl: number;
    source: string;
  };
  min_30d_paise_per_qtl: number;
  max_30d_paise_per_qtl: number;
  avg_30d_paise_per_qtl: number;
  change_7d_paise_per_qtl: number | null;
  change_7d_bps: number | null;
  history: PriceSeriesRes['points'];
  source_summary: Record<string, number>;
  forecast: {
    points: Array<{ target_date: string; p10_paise_per_qtl: number; p50_paise_per_qtl: number; p90_paise_per_qtl: number }>;
    source: string;
    is_model: boolean;
  };
  verdict: {
    action: string;
    hold_days?: number | null;
    expected_gain_paise?: number | null;
    worst_case_paise?: number | null;
    refusal_reason?: string | null;
    explain_mr?: string;
    explain_en?: string;
    confidence?: string;
    quantity_kg: number;
    itemised_costs?: Record<string, number> | null;
  };
  nearby: NearbyRes & {
    rows: Array<NearbyRes['rows'][number] & { name?: string; transport_source?: string }>;
  };
}

export const getMarketOverview = async (
  commodityId: string,
  marketId: string,
  districtId?: string,
): Promise<MarketOverview> =>
  get<MarketOverview>('/market/overview', { commodity_id: commodityId, market_id: marketId, district_id: districtId }, 20000);

// ─────────────────────────────────────────────────────────────────────────────
// AI & Forecasts
// ─────────────────────────────────────────────────────────────────────────────

/** One call to a backend agent tool. Read tools return facts; nothing here writes. */
export interface AgentToolResult {
  ok: boolean;
  tool: string;
  data?: any;
  card?: { type: string; data: any } | null;
  ui_action?: { type: string; target_screen: string; cta_label: string; params?: Record<string, unknown> } | null;
  citation?: { source: string; as_of?: string; mandi?: string } | null;
  error?: { code: string; message: string; missing: string[]; candidates: any[] };
}
export const runAgentTool = async (
  name: string,
  args: Record<string, unknown>,
  locale: Locale,
  screen: Record<string, string | null>,
): Promise<AgentToolResult> =>
  post<AgentToolResult>(`/agent/tools/${name}`, { args, locale, screen_context: screen }, 20000);

export const getForecast = async (commodityId: string, marketId: string, horizon = 14): Promise<ForecastRes> => {
  if (USE_FIXTURES) return getDynamicForecast(commodityId, marketId, horizon);
  return get<ForecastRes>('/ai/forecast', { commodity_id: commodityId, market_id: marketId, horizon }, 20000);
};

export const getModelCard = async (commodityId: string): Promise<ModelCard> => {
  if (USE_FIXTURES) return fxModelCard;
  return get<ModelCard>('/ai/model-card', { commodity_id: commodityId });
};

export const recommendWindow = async (body: WindowRecommendReq): Promise<WindowRes> => {
  if (USE_FIXTURES) return getDynamicWindowRecommendation(body);
  const res = await post<any>('/ai/window/recommend', body, 20000);
  return {
    ...res,
    costs: res.costs ?? res.itemised_costs,
    pledge_quote: res.pledge_quote
      ? { ...res.pledge_quote, warehouse_id: String(res.pledge_quote.warehouse_id ?? ''), is_worthwhile: true }
      : null,
  } as WindowRes;
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
  if (USE_FIXTURES) {
    return { ...fxLotListed, id: `lot_${Date.now()}`, commodity_id: body.commodity_id, market_id: body.market_id, qty_kg: body.qty_kg };
  }
  return toLot(await post<any>('/lots', body));
};

/** S22: set the asking price and list the lot to buyers. */
export const publishLot = async (lotId: string, pricePaisePerQtl: number): Promise<LotDto> => {
  if (USE_FIXTURES) return { ...fxLotListed, id: lotId };
  return toLot(await post<any>(`/lots/${lotId}/publish`, { expected_price_paise: pricePaisePerQtl }));
};

export const getLots = async (): Promise<LotDto[]> => {
  if (USE_FIXTURES) return getDynamicLots();
  const [lots] = await Promise.all([get<any[]>('/lots'), loadRefNames()]);
  return lots.map(toLot);
};

export const getLot = async (id: string): Promise<LotDto> => {
  if (USE_FIXTURES) return getDynamicLots().find(l => l.id === id) || fxLotListed;
  const [lot] = await Promise.all([get<any>(`/lots/${id}`), loadRefNames()]);
  return toLot(lot);
};

export const submitAssay = async (lotId: string, body: AssayReq): Promise<AssayRes> => {
  if (USE_FIXTURES) {
    return { score: 900, grade: 'A', weakest_dimension: 'damage_pct', tip_mr: '', tip_en: '' };
  }
  return post<AssayRes>(`/lots/${lotId}/assay`, body);
};

export const getLotAssay = async (lotId: string): Promise<AssayRecord> => {
  if (USE_FIXTURES) {
    return {
      lot_id: lotId, size_uniform: 3, colour_uniform: 3, sprouting: 3, damage_pct: 2,
      moisture_feel: 3, foreign_matter: 3, score: 944, grade: 'A', weakest_dimension: 'damage_pct',
      photo_path: null, created_at: new Date().toISOString(),
    };
  }
  return get<AssayRecord>(`/lots/${lotId}/assay`);
};

/** No pooling read API on the server yet — the split shown is illustrative. */
export const getPool = async (id: string): Promise<PoolDto> => {
  return {
    fpo: { id: 'fpo_1', name: 'Niphad Kanda Utpadak FPO', name_mr: 'निफाड कांदा उत्पादक FPO' },
    total_qty_kg: 14500,
    avg_score: 820,
    members: [],
    all_consented: false,
  } as unknown as PoolDto;
};

// ─────────────────────────────────────────────────────────────────────────────
// Demands, Matching, Offers
// ─────────────────────────────────────────────────────────────────────────────

export const getDemands = async (): Promise<DemandDto[]> => {
  if (USE_FIXTURES) return [fxDemand];
  return (await get<any[]>('/demands')).map(toDemand);
};

export const createDemand = async (body: {
  commodity_id: string;
  market_id: string;
  qty_kg: number;
  min_grade: string;
  bid_paise_per_qtl: number;
}): Promise<DemandDto> => {
  if (USE_FIXTURES) return fxDemand;
  return toDemand(
    await post<any>('/demands', {
      commodity_id: body.commodity_id,
      market_id: body.market_id,
      quantity_qtl: Math.max(1, Math.round(body.qty_kg / 100)),
      expected_price_paise: body.bid_paise_per_qtl,
      desired_grade: body.min_grade,
    }),
  );
};

export const getMatches = async (demandId: string): Promise<MatchesRes> => {
  if (USE_FIXTURES) return fxMatches;
  return get<MatchesRes>(`/demands/${demandId}/matches`);
};

export const getOffers = async (): Promise<OfferDto[]> => {
  if (USE_FIXTURES) return fxMyOffers;
  return get<OfferDto[]>('/offers');
};

export const getOfferThread = async (offerId: string): Promise<OfferDto[]> => {
  if (USE_FIXTURES) return fxThreadFor(offerId);
  return get<OfferDto[]>(`/offers/${offerId}/thread`);
};

export const createOffer = async (body: {
  demand_id?: string;
  lot_ids: string[];
  qty_kg: number;
  price_paise_per_qtl: number;
}): Promise<OfferDto> => {
  if (USE_FIXTURES) return { ...fxMyOffers[0], id: `off_${Date.now()}`, qty_kg: body.qty_kg, price_paise_per_qtl: body.price_paise_per_qtl } as OfferDto;
  return post<OfferDto>('/offers', body);
};

export const acceptOffer = async (offerId: string): Promise<TxDto> => {
  if (USE_FIXTURES) return fxTx;
  const res = await post<any>(`/offers/${offerId}/accept`);
  // The server returns the new transaction (or the offer, when escrow is off).
  if (res && res.offer_id !== undefined) {
    const offer = (await getOffers().catch(() => [] as OfferDto[])).find(o => o.id === String(res.offer_id));
    return toTx(res, offer);
  }
  return toTx({ id: '', offer_id: offerId, amount_paise: 0, status: 'CREATED' });
};

export const rejectOffer = async (offerId: string): Promise<OfferDto> => {
  if (USE_FIXTURES) return { ...fxMyOffers[0], id: offerId, status: 'REJECTED' } as OfferDto;
  return post<OfferDto>(`/offers/${offerId}/reject`);
};

export const counterOffer = async (
  offerId: string,
  body: { price_paise_per_qtl: number; note?: string },
): Promise<OfferDto> => {
  if (USE_FIXTURES) return { ...fxMyOffers[0], id: `off_counter_${Date.now()}`, round: 2, price_paise_per_qtl: body.price_paise_per_qtl, status: 'COUNTERED' } as OfferDto;
  return post<OfferDto>(`/offers/${offerId}/counter`, body);
};

// ─────────────────────────────────────────────────────────────────────────────
// Escrow & Disputes
// ─────────────────────────────────────────────────────────────────────────────

/** The caller's deals, newest first. */
export const getTransactions = async (): Promise<TxDto[]> => {
  if (USE_FIXTURES) return [fxTx];
  const [txs, offers] = await Promise.all([get<any[]>('/transactions'), getOffers().catch(() => [] as OfferDto[])]);
  return txs.map(t => toTx(t, offers.find(o => o.id === String(t.offer_id))));
};

export const getTransaction = async (id: string): Promise<TxDto> => {
  if (USE_FIXTURES) return fxTx;
  const [t, offers] = await Promise.all([get<any>(`/transactions/${id}`), getOffers().catch(() => [] as OfferDto[])]);
  return toTx(t, offers.find(o => o.id === String(t.offer_id)));
};

/** Escrow moves are one endpoint per action on the server; map the target state to it. */
export const transitionTx = async (txId: string, status: TxStatus): Promise<TxDto> => {
  if (USE_FIXTURES) return { ...fxTx, id: txId, status };
  const path: Partial<Record<TxStatus, string>> = {
    ESCROW_HELD: 'deposit',
    DISPATCHED: 'dispatch',
    DELIVERED: 'inspect',
    RELEASED: 'release',
  };
  const action = path[status];
  const t = action
    ? await post<any>(`/transactions/${txId}/${action}`, {})
    : await post<any>(`/transactions/${txId}/transition`, { action: status.toLowerCase() });
  return toTx(t);
};

export const getEscrowEvents = async (txId: string): Promise<EscrowEvent[]> => {
  if (USE_FIXTURES) return [];
  return (await get<any[]>(`/transactions/${txId}/events`)).map(toEvent);
};

export const createDispute = async (body: {
  tx_id: string;
  reason: DisputeReasonCode;
  description: string;
}): Promise<DisputeRes> => {
  if (USE_FIXTURES) {
    return {
      dispute: { id: `disp_${Date.now()}`, tx_id: body.tx_id, raised_by: '', reason_code: body.reason, description: body.description, photo_path: null, stage: 'RAISED', created_at: new Date().toISOString() },
      events: [],
    };
  }
  const d = await post<any>('/disputes', {
    transaction_id: Number(body.tx_id),
    reason: `${body.reason}: ${body.description}`.slice(0, 500),
  });
  return { dispute: toDispute(d), events: [] };
};

export const getDispute = async (id: string): Promise<DisputeRes> => {
  if (USE_FIXTURES) {
    return {
      dispute: { id, tx_id: 'tx_demo', raised_by: '', reason_code: 'QUALITY_MISMATCH', description: null, photo_path: null, stage: 'RAISED', created_at: new Date().toISOString() },
      events: [],
    };
  }
  return { dispute: toDispute(await get<any>(`/disputes/${id}`)), events: [] };
};

// ─────────────────────────────────────────────────────────────────────────────
// Data Provenance & Chat
// ─────────────────────────────────────────────────────────────────────────────

export const getDataProvenance = async (): Promise<ProvenanceRes> => {
  if (USE_FIXTURES) return { rows: [], generated_at: new Date().toISOString() };
  return get<ProvenanceRes>('/meta/data-provenance');
};

/** No messaging backend yet — these two stay illustrative in every mode. */
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
  ];
};

export const sendChatMessage = async (threadId: string, text: string): Promise<ChatMessage> => {
  const me = await getCachedUser();
  return {
    id: `msg_${Date.now()}`,
    sender_id: me?.id ?? 'me',
    sender_name: me?.name ?? '',
    text,
    created_at: new Date().toISOString(),
    is_me: true,
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// Voice — through our server (it holds the Sarvam key; the app holds none)
// ─────────────────────────────────────────────────────────────────────────────

export const transcribeAudio = async (
  uriOrFormData?: any,
  locale: Locale = 'mr',
): Promise<{ transcript: string; text?: string }> => {
  if (!uriOrFormData) throw new ApiError('NO_AUDIO', 'No recording to transcribe.', 0);
  let form: FormData;
  if (typeof FormData !== 'undefined' && uriOrFormData instanceof FormData) {
    form = uriOrFormData;
  } else {
    form = new FormData();
    if (typeof uriOrFormData === 'string' && (uriOrFormData.startsWith('blob:') || uriOrFormData.startsWith('data:'))) {
      const blob = await (await fetch(uriOrFormData)).blob(); // web recorder
      form.append('audio', blob, 'clip.webm');
    } else if (typeof Blob !== 'undefined' && uriOrFormData instanceof Blob) {
      form.append('audio', uriOrFormData, 'clip.webm');
    } else {
      // React Native: a file uri from the recorder
      form.append('audio', { uri: String(uriOrFormData), name: 'clip.m4a', type: 'audio/m4a' } as any);
    }
  }
  form.append('locale', locale);
  const res = await request<{ transcript: string }>('POST', '/voice/transcribe', { form, timeoutMs: 30000 });
  return { transcript: res.transcript, text: res.transcript };
};

export const narrate = async (
  text: string,
  locale: Locale = 'mr',
  _speaker?: string,
  _pace?: number,
): Promise<{ audio_base64: string }> => {
  try {
    const res = await post<{ audio_base64: string }>('/voice/narrate', { text, locale }, 30000);
    return { audio_base64: res.audio_base64 || '' };
  } catch {
    // Callers fall back to on-device speech when this is empty.
    return { audio_base64: '' };
  }
};
