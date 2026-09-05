/**
 * Mandi-Setu Voice Module — Configuration & Environment Settings
 */

import * as fs from 'fs';
import * as path from 'path';

// Helper to load .env manually if dotenv is not present in runtime
function loadLocalEnv(): Record<string, string> {
  const env: Record<string, string> = {};
  const envPaths = [
    path.resolve(process.cwd(), '.env'),
    path.resolve(process.cwd(), '../../.env'),
  ];

  for (const envPath of envPaths) {
    if (fs.existsSync(envPath)) {
      try {
        const content = fs.readFileSync(envPath, 'utf8');
        for (const line of content.split('\n')) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) continue;
          const eqIdx = trimmed.indexOf('=');
          if (eqIdx !== -1) {
            const key = trimmed.slice(0, eqIdx).trim();
            const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
            env[key] = val;
          }
        }
      } catch {
        // ignore
      }
      break;
    }
  }
  return env;
}

const localEnv = typeof process !== 'undefined' ? loadLocalEnv() : {};

function getEnv(key: string, defaultVal = ''): string {
  if (typeof process !== 'undefined' && process.env && process.env[key]) {
    return process.env[key]!;
  }
  if (localEnv[key]) {
    return localEnv[key];
  }
  return defaultVal;
}

export interface VoiceConfig {
  // Sarvam AI
  sarvamApiKey: string;
  sarvamTtsEndpoint: string;
  sarvamAsrEndpoint: string;
  sarvamNormalizeEndpoint: string;
  sarvamTtsSpeaker: string;
  sarvamTtsModel: string;
  sarvamAsrModel: string;
  
  // Bhashini (Fallback)
  bhashiniApiKey: string;
  bhashiniUserId: string;
  bhashiniPipelineId: string;
  bhashiniInferenceEndpoint: string;

  // Audio / Speech Tunables
  confidenceThreshold: number;
  maxRecordingSeconds: number;
  cacheEnabled: boolean;
  defaultLanguage: string;
}

export const VOICE_CONFIG: VoiceConfig = {
  sarvamApiKey: getEnv('SARVAM_API_KEY'),
  sarvamTtsEndpoint: getEnv('SARVAM_TTS_ENDPOINT', 'https://api.sarvam.ai/text-to-speech'),
  sarvamAsrEndpoint: getEnv('SARVAM_ASR_ENDPOINT', 'https://api.sarvam.ai/speech-to-text'),
  sarvamNormalizeEndpoint: getEnv('SARVAM_NORMALIZE_ENDPOINT', 'https://api.sarvam.ai/v1/chat/completions'),
  sarvamTtsSpeaker: getEnv('SARVAM_TTS_SPEAKER', 'shubh'),
  sarvamTtsModel: 'bulbul:v3',
  sarvamAsrModel: 'saaras:v3',

  bhashiniApiKey: getEnv('BHASHINI_API_KEY'),
  bhashiniUserId: getEnv('BHASHINI_USER_ID'),
  bhashiniPipelineId: getEnv('BHASHINI_PIPELINE_ID'),
  bhashiniInferenceEndpoint: getEnv('BHASHINI_INFERENCE_ENDPOINT', 'https://dhruva-api.bhashini.gov.in/services/inference/pipeline'),

  confidenceThreshold: parseFloat(getEnv('VOICE_CONFIDENCE_THRESHOLD', '0.6')),
  maxRecordingSeconds: parseInt(getEnv('VOICE_MAX_RECORDING_SECONDS', '10'), 10),
  cacheEnabled: getEnv('VOICE_CACHE_ENABLED', 'true') !== 'false',
  defaultLanguage: 'mr-IN',
};

/**
 * Checks whether live Sarvam API integration is available
 */
export function isSarvamConfigured(): boolean {
  return Boolean(VOICE_CONFIG.sarvamApiKey && VOICE_CONFIG.sarvamApiKey.trim().length > 0);
}

/**
 * Checks whether live Bhashini API integration is available
 */
export function isBhashiniConfigured(): boolean {
  return Boolean(
    VOICE_CONFIG.bhashiniApiKey &&
    VOICE_CONFIG.bhashiniUserId &&
    VOICE_CONFIG.bhashiniPipelineId
  );
}
