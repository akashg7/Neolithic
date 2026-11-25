/**
 * The single seam between the chat UI and the backend agent (`/api/v1/agent/*`).
 *
 * - `USE_FIXTURES`: offline canned demo replies (`mockAgentReply`).
 * - Live API: calls `POST /api/v1/agent/chat` (and normalizes backend cards/intents
 *   into the exact UI contract). If `/agent/chat` is unavailable or returns
 *   `LLM_UNAVAILABLE` (e.g. no provider key configured yet), falls back cleanly to
 *   `toolAgentReply` (deterministic `/agent/tools` without an LLM).
 */
import { USE_FIXTURES } from '../config';
import type {
  AgentCard,
  AgentChatRequest,
  AgentChatResponse,
  AgentIntent,
  Citation,
  WindowAction,
} from './agentTypes';
import { deleteAgentSession, postAgentChat, postAgentVoiceChat } from './api';
import { mockAgentReply } from './mockAgent';
import { toolAgentReply } from './toolAgent';

const INTENT_MAP: Record<string, AgentIntent> = {
  PRICE: 'CHECK_PRICE',
  WINDOW: 'SALE_WINDOW',
  LOT: 'CREATE_LOT',
  ONBOARD: 'REGISTER',
  RAG: 'KNOWLEDGE',
  GRADE: 'KNOWLEDGE',
  PORTFOLIO: 'KNOWLEDGE',
  NAVIGATE: 'UNKNOWN',
  SMALLTALK: 'UNKNOWN',
  OUT_OF_SCOPE: 'UNKNOWN',
};

function normalizeWindowAction(raw: unknown): WindowAction {
  const s = String(raw || '').toUpperCase();
  if (s === 'SELL_ELSEWHERE') return 'SELL_ELSEWHERE';
  if (s === 'SELL_NOW' || s === 'SELL') return 'SELL';
  if (s === 'HOLD') return 'HOLD';
  if (s === 'SPLIT') return 'SPLIT';
  return 'NO_ADVICE';
}

function normalizeCards(rawCards: any[]): AgentCard[] {
  const out: AgentCard[] = [];
  for (const raw of rawCards || []) {
    if (!raw || !raw.type) continue;
    const d = raw.data || {};
    if (raw.type === 'WINDOW_VERDICT') {
      out.push({
        type: 'WINDOW_VERDICT',
        data: {
          action: normalizeWindowAction(d.action),
          hold_days: d.hold_days ?? undefined,
          expected_gain_paise: d.expected_gain_paise ?? undefined,
          worst_case_paise: d.worst_case_paise ?? undefined,
          uncertainty_pct: d.uncertainty_pct ?? (d.band_width_bps != null ? Math.round(Number(d.band_width_bps) / 100) : undefined),
          commodity: String(d.commodity || ''),
          mandi: String(d.mandi || ''),
          quantity_kg: Number(d.quantity_kg || 0),
          alt_market: d.alt_market ?? null,
        },
      });
    } else if (raw.type === 'PRICE_SNAPSHOT') {
      const modal = Number(d.modal_price_paise_per_qtl ?? d.modal_paise_per_qtl ?? 0);
      const rawSeries = Array.isArray(d.series_paise_per_qtl)
        ? d.series_paise_per_qtl.map((v: any) => Number(v)).filter((v: number) => Number.isFinite(v))
        : [];
      out.push({
        type: 'PRICE_SNAPSHOT',
        data: {
          commodity: String(d.commodity || ''),
          mandi: String(d.mandi || ''),
          change_bps: d.change_bps ?? null,
          obs_date: d.obs_date ?? undefined,
          modal_price_paise_per_qtl: modal,
          series_paise_per_qtl: rawSeries.length ? rawSeries : modal ? [modal] : [],
          source: d.source || 'ARCHIVE',
        },
      });
    } else if (raw.type === 'LOT_DRAFT') {
      out.push({
        type: 'LOT_DRAFT',
        data: {
          commodity: String(d.commodity || ''),
          mandi: String(d.mandi || ''),
          quantity_kg: Number(d.quantity_kg || 0),
          ...(d.commodity_id ? { commodity_id: String(d.commodity_id) } : {}),
          ...(d.market_id ? { market_id: String(d.market_id) } : {}),
        },
      });
    } else if (raw.type === 'CONFIRM_ACTION' && d.action === 'CREATE_LOT') {
      const sum = d.summary || {};
      const body = d.body || {};
      out.push({
        type: 'LOT_DRAFT',
        data: {
          commodity: String(sum.commodity || ''),
          mandi: String(sum.mandi || ''),
          quantity_kg: Number(sum.quantity_kg || 0),
          ...(body.commodity_id ? { commodity_id: String(body.commodity_id) } : {}),
          ...(body.market_id ? { market_id: String(body.market_id) } : {}),
        },
      });
    } else if (raw.type === 'RAG_CITATION') {
      const chunks = Array.isArray(d.chunks)
        ? d.chunks.map((c: any) => ({
            chunk_id: String(c?.chunk_id || ''),
            source_doc: String(c?.source_doc || ''),
            section_title: c?.section_title ? String(c.section_title) : undefined,
            category: c?.category ? String(c.category) : undefined,
            score: typeof c?.score === 'number' ? c.score : undefined,
            snippet: String(c?.snippet ?? c?.text ?? ''),
          }))
        : [];
      if (chunks.length) {
        out.push({
          type: 'RAG_CITATION',
          data: {
            query: String(d.query || ''),
            chunks,
          },
        });
      }
    } else if (raw.type === 'ONBOARD_PROFILE') {
      out.push({
        type: 'ONBOARD_PROFILE',
        data: {
          name: d.name ?? null,
          village: d.village ?? null,
          district_id: d.district_id ?? null,
          district_name: d.district_name ?? null,
        },
      });
    }
  }
  return out;
}

function normalizeCitations(raw: any[]): Citation[] {
  const seen = new Set<string>();
  const out: Citation[] = [];
  for (const c of raw || []) {
    if (!c || !c.source) continue;
    const source = String(c.source);
    const title = String(c.title || c.section_title || source);
    const key = `${source}::${title}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      source,
      title,
      as_of: c.as_of ?? null,
      chunk_id: c.chunk_id ?? null,
      section_title: c.section_title ?? null,
    });
  }
  return out;
}

export function normalizeAgentResponse(raw: any): AgentChatResponse {
  const intent = INTENT_MAP[String(raw?.intent_detected || '')] ?? (raw?.intent_detected as AgentIntent) ?? 'UNKNOWN';
  return {
    session_id: String(raw?.session_id || ''),
    turn_id: raw?.turn_id ?? undefined,
    transcript: raw?.transcript ?? null,
    intent_detected: intent,
    reply_text: String(raw?.reply_text || ''),
    audio_base64: raw?.audio_base64 ?? null,
    cards: normalizeCards(raw?.cards || []),
    ui_action: raw?.ui_action
      ? {
          type: raw.ui_action.type === 'PREFILL' ? 'PREFILL' : 'OFFER_NAVIGATION',
          target_screen: String(raw.ui_action.target_screen || ''),
          cta_label: String(raw.ui_action.cta_label || ''),
          params: raw.ui_action.params || undefined,
        }
      : null,
    citations: normalizeCitations(raw?.citations || []),
    quick_replies: Array.isArray(raw?.quick_replies) ? raw.quick_replies.map(String).slice(0, 3) : [],
    error_code: raw?.error_code ?? null,
  };
}

export async function sendChatMessage(req: AgentChatRequest): Promise<AgentChatResponse> {
  if (USE_FIXTURES) return mockAgentReply(req);
  try {
    const raw = await postAgentChat<any>(req as unknown as Record<string, unknown>);
    if (raw?.error_code === 'LLM_UNAVAILABLE') {
      return toolAgentReply(req);
    }
    return normalizeAgentResponse(raw);
  } catch {
    return toolAgentReply(req);
  }
}

export async function sendVoiceChatMessage(
  audioUriOrBlob: unknown,
  meta: Omit<AgentChatRequest, 'message'>,
): Promise<AgentChatResponse> {
  const form = new FormData();
  if (typeof audioUriOrBlob === 'string' && (audioUriOrBlob.startsWith('blob:') || audioUriOrBlob.startsWith('data:'))) {
    const blob = await (await fetch(audioUriOrBlob)).blob();
    form.append('audio', blob, 'clip.webm');
  } else if (typeof Blob !== 'undefined' && audioUriOrBlob instanceof Blob) {
    form.append('audio', audioUriOrBlob, 'clip.webm');
  } else {
    form.append('audio', { uri: String(audioUriOrBlob), name: 'clip.m4a', type: 'audio/m4a' } as any);
  }
  form.append('session_id', meta.session_id);
  form.append('locale', meta.locale);
  form.append('screen_context', JSON.stringify(meta.screen_context));
  form.append('include_audio', String(meta.include_audio));

  const raw = await postAgentVoiceChat<any>(form);
  return normalizeAgentResponse(raw);
}

export async function resetAgentSession(sessionId: string): Promise<void> {
  if (USE_FIXTURES || !sessionId) return;
  try {
    await deleteAgentSession(sessionId);
  } catch {
    /* session clear is best-effort */
  }
}
