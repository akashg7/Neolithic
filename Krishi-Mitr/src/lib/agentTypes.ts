/**
 * Agent chat contract — Phase 0 "Contract 1" of NLP_Execution_Plan.md §4.
 * Frozen: the UI renders exactly these shapes, and Member 5's
 * `POST /agent/chat` returns them. Do not add UI-only fields here.
 */
import type { Locale } from '../types/api';

export type AgentIntent =
  | 'CHECK_PRICE'
  | 'SALE_WINDOW'
  | 'CREATE_LOT'
  | 'REGISTER'
  | 'KNOWLEDGE'
  | 'UNKNOWN'
  | 'PRICE'
  | 'WINDOW'
  | 'LOT'
  | 'GRADE'
  | 'PORTFOLIO'
  | 'RAG'
  | 'ONBOARD'
  | 'NAVIGATE'
  | 'SMALLTALK'
  | 'OUT_OF_SCOPE';

export interface ScreenContext {
  current_screen: string;
  active_commodity_id: string | null;
  active_market_id: string | null;
  active_lot_id: string | null;
}

export interface AgentChatRequest {
  session_id: string;
  message: string;
  locale: Locale;
  screen_context: ScreenContext;
  include_audio: boolean;
}

export type WindowAction = 'HOLD' | 'SPLIT' | 'SELL' | 'NO_ADVICE';

export interface WindowVerdictCardData {
  action: WindowAction;
  hold_days?: number;
  /** Integer paise. Absent when action is NO_ADVICE. */
  expected_gain_paise?: number;
  worst_case_paise?: number;
  /** 0-100, shown only for NO_ADVICE (the forecast band was too wide). */
  uncertainty_pct?: number;
  commodity: string;
  mandi: string;
  quantity_kg: number;
}

export interface PriceSnapshotCardData {
  commodity: string;
  mandi: string;
  change_bps?: number | null;
  obs_date?: string;
  /** Integer paise per quintal. */
  modal_price_paise_per_qtl: number;
  /** Last 7 days, oldest first, integer paise per quintal. */
  series_paise_per_qtl: number[];
  source: 'AGMARKNET' | 'MSAMB' | 'ARCHIVE' | 'IMPUTED' | 'SYNTHETIC';
}

export interface LotDraftCardData {
  commodity: string;
  mandi: string;
  quantity_kg: number;
}

export type AgentCard =
  | { type: 'WINDOW_VERDICT'; data: WindowVerdictCardData }
  | { type: 'PRICE_SNAPSHOT'; data: PriceSnapshotCardData }
  | { type: 'LOT_DRAFT'; data: LotDraftCardData };

export interface UiAction {
  type: 'OFFER_NAVIGATION' | 'PREFILL';
  target_screen: string;
  cta_label: string;
  params?: Record<string, unknown>;
}

export interface Citation {
  source: string;
  title: string;
  as_of?: string | null;
  chunk_id?: string | null;
  section_title?: string | null;
}

export interface AgentChatResponse {
  session_id: string;
  turn_id?: string;
  transcript: string | null;
  intent_detected: AgentIntent;
  reply_text: string;
  audio_base64: string | null;
  cards: AgentCard[];
  ui_action: UiAction | null;
  citations: Citation[];
  quick_replies: string[];
  error_code?: string | null;
}

/** A turn as the UI stores it. Client-side only. */
export type ChatMessage =
  | { id: string; role: 'user'; text: string; at: number }
  | { id: string; role: 'assistant'; response: AgentChatResponse; at: number }
  | { id: string; role: 'error'; text: string; retryText: string; at: number };
