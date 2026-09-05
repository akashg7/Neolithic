/**
 * Mandi-Setu Voice Module — Sarvam Bulbul TTS API Wrapper
 * Converts Marathi sentences into spoken audio using Sarvam's Bulbul v1 model.
 */

import { VOICE_CONFIG, isSarvamConfigured } from './config';
import type { AudioSource } from './types';

export interface SarvamTTSRequest {
  inputs: string[];
  target_language_code: string;
  speaker: string;
  pitch?: number;
  pace?: number;
  loudness?: number;
  speech_sample_rate?: number;
  enable_preprocessing?: boolean;
  model?: string;
}

export interface SarvamTTSResponse {
  audios: string[]; // array of base64 encoded audio strings
}

/**
 * Calls Sarvam Bulbul TTS API to synthesize text into audio.
 * Returns base64 encoded audio or data URI.
 */
export async function synthesizeMarathiSpeech(text: string): Promise<AudioSource> {
  if (!text || text.trim().length === 0) {
    throw new Error('Cannot synthesize empty speech text');
  }

  if (!isSarvamConfigured()) {
    throw new Error('SARVAM_API_KEY is not configured in environment.');
  }

  const payload: SarvamTTSRequest = {
    inputs: [text],
    target_language_code: VOICE_CONFIG.defaultLanguage, // 'mr-IN'
    speaker: VOICE_CONFIG.sarvamTtsSpeaker, // e.g. 'meera'
    pitch: 0,
    pace: 1.0,
    loudness: 1.0,
    speech_sample_rate: 22050,
    enable_preprocessing: true,
    model: VOICE_CONFIG.sarvamTtsModel,
  };

  const response = await fetch(VOICE_CONFIG.sarvamTtsEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-subscription-key': VOICE_CONFIG.sarvamApiKey,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(`Sarvam TTS API error (${response.status}): ${errorText}`);
  }

  const data = (await response.json()) as SarvamTTSResponse;

  if (!data.audios || data.audios.length === 0 || !data.audios[0]) {
    throw new Error('Sarvam TTS returned empty audio payload');
  }

  const base64Audio = data.audios[0];
  const uri = `data:audio/wav;base64,${base64Audio}`;

  return {
    uri,
    base64: base64Audio,
    isLocalFile: false,
  };
}
