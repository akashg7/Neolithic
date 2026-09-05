/**
 * Mandi-Setu Voice Module — Text Normalizer (Track B: B3)
 * Uses Sarvam-1 / Mayura (or local Marathi linguistic rule-based cleaner when offline)
 * to strip conversational filler words and normalize ASR transcripts before matching.
 */

import { VOICE_CONFIG, isSarvamConfigured } from './config';

export interface NormalizedVoiceEntities {
  cleaned_text: string;
  raw_commodity_phrase?: string;
  raw_quantity_phrase?: string;
  raw_market_phrase?: string;
  confidence: number;
}

// Common Marathi conversational filler phrases
const MARATHI_FILLERS = [
  /\bअरे\b/g,
  /\bभावा\b/g,
  /\bदादा\b/g,
  /\bमाझ्याकडे\b/g,
  /\bसाधारण\b/g,
  /\bसुमारे\b/g,
  /\bआहे\b/g,
  /\bहोते\b/g,
  /\bविकायचा\s+आहे\b/g,
  /\bविकायचे\s+आहे\b/g,
  /\bद्यायचा\s+आहे\b/g,
  /\bबाजारामध्ये\b/g,
  /\bबाजारपेठेत\b/g,
  /\bमार्केटला\b/g,
  /\bमार्केटमध्ये\b/g,
  /\bअं+\b/g,
  /\bम्हणजे\b/g,
  /\bतर\b/g,
];

/**
 * Local rule-based Marathi linguistic normalizer (offline resilient)
 */
export function normalizeTranscriptLocally(rawTranscript: string): NormalizedVoiceEntities {
  if (!rawTranscript) {
    return { cleaned_text: '', confidence: 0 };
  }

  let cleaned = rawTranscript;
  for (const filler of MARATHI_FILLERS) {
    cleaned = cleaned.replace(filler, ' ');
  }

  cleaned = cleaned.replace(/[,\.।?!]/g, ' ').replace(/\s+/g, ' ').trim();

  return {
    cleaned_text: cleaned,
    confidence: 0.85,
  };
}

/**
 * Normalizes raw ASR transcript using Sarvam-1 / Mayura LLM when live,
 * or gracefully degrades to local linguistic normalizer when offline.
 */
export async function normalizeVoiceTranscript(rawTranscript: string): Promise<NormalizedVoiceEntities> {
  if (!rawTranscript || rawTranscript.trim().length === 0) {
    return { cleaned_text: '', confidence: 0 };
  }

  // 1. If Sarvam is configured, call Sarvam-1 / Mayura
  if (isSarvamConfigured()) {
    try {
      const prompt = `तुम्ही मराठी कृषी बाजाराचे सहाय्यक आहात. खालील वाक्यातून शेतमालाचे नाव, प्रमाण (संख्या व एकक), आणि बाजाराचे नाव ओळखा.
वाक्य: "${rawTranscript}"
फक्त JSON स्वरूपात उत्तर द्या:
{"commodity": string, "quantity": string, "market": string}`;

      const response = await fetch(VOICE_CONFIG.sarvamNormalizeEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'api-subscription-key': VOICE_CONFIG.sarvamApiKey,
        },
        body: JSON.stringify({
          model: 'sarvam-1',
          messages: [{ role: 'user', content: prompt }],
          temperature: 0.1,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const content = data?.choices?.[0]?.message?.content;
        if (content) {
          const jsonMatch = content.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            return {
              cleaned_text: `${parsed.commodity || ''} ${parsed.quantity || ''} ${parsed.market || ''}`.trim(),
              raw_commodity_phrase: parsed.commodity,
              raw_quantity_phrase: parsed.quantity,
              raw_market_phrase: parsed.market,
              confidence: 0.95,
            };
          }
        }
      }
    } catch (llmErr) {
      console.warn('Sarvam-1 normalization API call failed, falling back to local normalizer:', llmErr);
    }
  }

  // 2. Fallback to local linguistic normalizer
  return normalizeTranscriptLocally(rawTranscript);
}
