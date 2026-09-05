/**
 * Mandi-Setu Voice Module — TTS Fallback Ladder (Track A: Voice-OUT)
 * Priority ladder: Sarvam Bulbul -> Bhashini TTS -> Device-Native / Expo-Speech -> Text-Only UI
 */

import { synthesizeMarathiSpeech } from './sarvamTTS';
import { VOICE_CONFIG, isBhashiniConfigured } from './config';
import type { AudioSource } from './types';

export type TTSFallbackEvent = 'sarvam_tts_failed' | 'bhashini_tts_failed' | 'device_speech_used';

export function logTTSFallback(event: TTSFallbackEvent, error?: unknown) {
  console.warn(`[TTS Fallback] ${event}:`, error instanceof Error ? error.message : error);
}

/**
 * Secondary fallback: Bhashini TTS API
 */
export async function synthesizeBhashiniSpeech(text: string): Promise<AudioSource> {
  if (!isBhashiniConfigured()) {
    throw new Error('Bhashini credentials not configured.');
  }

  const payload = {
    pipelineTasks: [
      {
        taskType: 'tts',
        config: {
          language: { sourceLanguage: 'mr' },
          gender: 'female',
          samplingRate: 22050,
        },
      },
    ],
    inputData: {
      input: [{ source: text }],
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
    throw new Error(`Bhashini TTS failed with status ${response.status}`);
  }

  const data = await response.json();
  const audioContent = data?.pipelineResponse?.[0]?.audio?.[0]?.audioContent;
  if (!audioContent) {
    throw new Error('Bhashini returned empty audioContent');
  }

  return {
    uri: `data:audio/wav;base64,${audioContent}`,
    base64: audioContent,
    isLocalFile: false,
  };
}

/**
 * Device-native / Expo-Speech fallback representation
 */
export async function synthesizeDeviceNativeSpeech(text: string): Promise<AudioSource> {
  logTTSFallback('device_speech_used', `Spoken via device-native TTS: "${text}"`);
  return {
    uri: `device-native://speech?text=${encodeURIComponent(text)}&lang=mr-IN`,
    isLocalFile: false,
  };
}

/**
 * Main TTS entry point with cascading fallback ladder:
 * Sarvam Bulbul -> Bhashini -> Device Native
 */
export async function synthesizeWithFallback(text: string): Promise<AudioSource> {
  // 1. Primary: Sarvam Bulbul
  try {
    return await synthesizeMarathiSpeech(text);
  } catch (errSarvam) {
    logTTSFallback('sarvam_tts_failed', errSarvam);

    // 2. Secondary: Bhashini
    try {
      return await synthesizeBhashiniSpeech(text);
    } catch (errBhashini) {
      logTTSFallback('bhashini_tts_failed', errBhashini);

      // 3. Tertiary: Device-native / expo-speech
      return await synthesizeDeviceNativeSpeech(text);
    }
  }
}
