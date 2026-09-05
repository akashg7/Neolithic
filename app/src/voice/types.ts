/**
 * Mandi-Setu Voice Module — Shared Contracts & Types
 * Mirroring backend wire format (snake_case) and defining Voice Out/In provider interfaces.
 */

// ============================================================================
// 1. Backend Wire Format Schemas (mirroring /ai/window/recommend & /ai/pledge/quote)
// ============================================================================

export type WindowAction = 'SELL_NOW' | 'SELL_ELSEWHERE' | 'HOLD' | 'SPLIT' | 'NO_ADVICE';

export type RefusalReason =
  | 'BAND_TOO_WIDE'
  | 'INSUFFICIENT_HISTORY'
  | 'STALE_DATA'
  | 'GAIN_BELOW_COST';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface CostBreakdown {
  storage_paise_per_qtl?: number;
  spoilage_paise_per_qtl?: number;
  transport_paise_per_qtl?: number;
  interest_paise_per_qtl?: number;
  total_cost_paise_per_qtl?: number;
}

export interface WindowRes {
  action: WindowAction;
  hold_days: number | null;
  confidence: ConfidenceLevel;
  expected_gain_paise: number | null;
  worst_case_paise: number | null;
  refusal_reason: RefusalReason | null;
  sell_now_net_paise_per_qtl: number;
  hold_p50_net_paise_per_qtl?: number | null;
  hold_p10_net_paise_per_qtl?: number | null;
  band_width_bps?: number;
  costs?: CostBreakdown;
  explain_mr?: string;
  explain_en?: string;
}

export interface PledgeQuote {
  loan_paise: number;
  interest_paise: number;
  days: number;
  rate_bps_annual: number;
  is_worthwhile: boolean;
  disclaimer: string;
}

export type AssayQuestionId =
  | 'size_uniform'
  | 'colour_uniform'
  | 'sprouting'
  | 'damage_pct'
  | 'moisture_feel'
  | 'foreign_matter';

export interface AssayQuestion {
  id: AssayQuestionId;
  prompt_mr: string;
}

// ============================================================================
// 2. Voice-IN (ASR & Structuring) Contracts
// ============================================================================

export interface ASRResult {
  raw_transcript: string;
  confidence: number; // 0 to 1
  language_code?: string;
}

export interface ParsedLotFields {
  commodity_id: string | null;
  commodity_name_mr?: string | null;
  commodity_confidence: number;
  qty_kg: number | null;
  qty_confidence: number;
  market_id: string | null;
  market_name_mr?: string | null;
  market_confidence: number;
}

export type RegistrationField = 'name' | 'district' | 'village' | 'primary_commodity';

export interface ParsedRegistrationField {
  field_name: RegistrationField;
  raw_value: string;
  confidence: number;
}

// ============================================================================
// 3. Fallback Ladder & Provider Interfaces
// ============================================================================

export interface AudioSource {
  uri: string;
  base64?: string;
  isLocalFile?: boolean;
}

export interface VoiceOutProvider {
  name: 'sarvam' | 'bhashini' | 'expo-speech' | 'device-native';
  synthesize(text: string): Promise<AudioSource>;
}

export interface VoiceInProvider {
  name: 'sarvam' | 'bhashini';
  recognize(audioBlobOrUri: string | Blob): Promise<ASRResult>;
}

export class VoiceInUnavailableError extends Error {
  constructor(message = 'Voice recognition is unavailable offline. Please enter details manually.') {
    super(message);
    this.name = 'VoiceInUnavailableError';
  }
}

// ============================================================================
// 4. Component Props Interfaces
// ============================================================================

export interface SpeakerButtonProps {
  text: string;
  autoPlayOnMount?: boolean;
  size?: 'small' | 'medium' | 'large';
  onPlayStart?: () => void;
  onPlayEnd?: () => void;
  onError?: (error: Error) => void;
}

export interface VoiceInputButtonProps {
  onResult: (fields: ParsedLotFields | ParsedRegistrationField) => void;
  parseMode: 'lot_creation' | 'registration_field';
  fieldName?: RegistrationField;
  onError?: (error: Error) => void;
}

export interface FieldVerification {
  value: string;
  confidence: number;
  label_mr?: string;
}

export interface VoiceConfirmSheetProps {
  parsedFields: Record<string, FieldVerification>;
  onConfirm: () => void;
  onEdit: (fieldName: string) => void;
  onCancel?: () => void;
}
