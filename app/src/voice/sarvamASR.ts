/**
 * Mandi-Setu Voice Module — Sarvam Saaras ASR API Wrapper (Track B: Voice-IN)
 * Transcribes spoken audio into Marathi text with confidence score using Sarvam Saaras.
 */

import { VOICE_CONFIG, isSarvamConfigured } from './config';
import type { ASRResult } from './types';

/**
 * Sends audio to Sarvam Saaras API for speech-to-text transcription.
 * @param audioBlobOrBuffer Audio file Blob (in browser/RN) or Buffer (in Node) or file object
 * @param filename Optional audio filename (e.g. 'recording.wav')
 */
export async function transcribeMarathiSpeech(
  audioBlobOrBuffer: Blob | Buffer | Uint8Array | { uri: string; name?: string; type?: string },
  filename = 'recording.wav'
): Promise<ASRResult> {
  if (!isSarvamConfigured()) {
    throw new Error('SARVAM_API_KEY is not configured.');
  }

  const formData = new FormData();

  if (typeof Blob !== 'undefined' && audioBlobOrBuffer instanceof Blob) {
    formData.append('file', audioBlobOrBuffer, filename);
  } else if (typeof Buffer !== 'undefined' && Buffer.isBuffer(audioBlobOrBuffer)) {
    const blob = new Blob([audioBlobOrBuffer], { type: 'audio/wav' });
    formData.append('file', blob, filename);
  } else if (typeof audioBlobOrBuffer === 'object' && 'uri' in audioBlobOrBuffer) {
    // React Native FormData asset format
    formData.append('file', audioBlobOrBuffer as any);
  } else {
    formData.append('file', new Blob([audioBlobOrBuffer as any], { type: 'audio/wav' }), filename);
  }

  formData.append('language_code', VOICE_CONFIG.defaultLanguage); // 'mr-IN'
  formData.append('model', VOICE_CONFIG.sarvamAsrModel); // 'saaras:v3'
  formData.append('mode', 'transcribe');

  const response = await fetch(VOICE_CONFIG.sarvamAsrEndpoint, {
    method: 'POST',
    headers: {
      'api-subscription-key': VOICE_CONFIG.sarvamApiKey,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => response.statusText);
    throw new Error(`Sarvam Saaras ASR failed (${response.status}): ${errorBody}`);
  }

  const data = await response.json();

  const transcript = data.transcript || '';
  const confidence = typeof data.confidence === 'number' ? data.confidence : 0.85;

  return {
    raw_transcript: transcript.trim(),
    confidence,
    language_code: VOICE_CONFIG.defaultLanguage,
  };
}
