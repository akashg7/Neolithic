/**
 * Mandi-Setu Voice Module — ASR Fallback Ladder (Track B: B5)
 * Priority ladder: Sarvam Saaras -> Bhashini ASR -> throw VoiceInUnavailableError.
 * Invariant: Voice-IN has no offline fallback; errors must trigger graceful manual form entry.
 */

import { transcribeMarathiSpeech } from './sarvamASR';
import { VOICE_CONFIG, isBhashiniConfigured } from './config';
import { VoiceInUnavailableError, type ASRResult } from './types';

export type ASRFallbackEvent = 'sarvam_asr_failed' | 'bhashini_asr_failed' | 'asr_unavailable_offline';

export function logASRFallback(event: ASRFallbackEvent, error?: unknown) {
  console.warn(`[ASR Fallback] ${event}:`, error instanceof Error ? error.message : error);
}

/**
 * Secondary fallback: Bhashini ASR API
 */
export async function transcribeBhashiniSpeech(audioBlobOrBuffer: any): Promise<ASRResult> {
  if (!isBhashiniConfigured()) {
    throw new Error('Bhashini credentials not configured.');
  }

  let base64Audio = '';
  if (typeof audioBlobOrBuffer === 'string') {
    base64Audio = audioBlobOrBuffer;
  } else if (typeof Buffer !== 'undefined' && Buffer.isBuffer(audioBlobOrBuffer)) {
    base64Audio = audioBlobOrBuffer.toString('base64');
  }

  const payload = {
    pipelineTasks: [
      {
        taskType: 'asr',
        config: {
          language: { sourceLanguage: 'mr' },
          audioFormat: 'wav',
          samplingRate: 16000,
        },
      },
    ],
    inputData: {
      audio: [{ audioContent: base64Audio }],
    },
  };

  const response = await fetch(VOICE_CONFIG.bhashiniInferenceEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: VOICE_CONFIG.bhashiniApiKey,
      userID: VOICE_CONFIG.bhashiniUserId,
      pipelineId: VOICE_CONFIG.bhashiniPipelineId,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Bhashini ASR failed with status ${response.status}`);
  }

  const data = await response.json();
  const transcript = data?.pipelineResponse?.[0]?.output?.[0]?.source || '';

  return {
    raw_transcript: transcript,
    confidence: 0.85,
    language_code: 'mr-IN',
  };
}

/**
 * Main ASR entry point with fallback ladder:
 * Sarvam Saaras -> Bhashini -> VoiceInUnavailableError
 */
export async function recognizeWithFallback(audioBlobOrBuffer: any): Promise<ASRResult> {
  // 1. Primary: Sarvam Saaras
  try {
    return await transcribeMarathiSpeech(audioBlobOrBuffer);
  } catch (errSarvam) {
    logASRFallback('sarvam_asr_failed', errSarvam);

    // 2. Secondary: Bhashini
    try {
      return await transcribeBhashiniSpeech(audioBlobOrBuffer);
    } catch (errBhashini) {
      logASRFallback('bhashini_asr_failed', errBhashini);

      // 3. No offline ASR exists: throw VoiceInUnavailableError
      logASRFallback('asr_unavailable_offline');
      throw new VoiceInUnavailableError();
    }
  }
}
