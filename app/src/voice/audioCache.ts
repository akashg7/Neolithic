/**
 * Mandi-Setu Voice Module — Audio Cache (Track A: Voice-OUT)
 * Hashes exact Marathi sentence to cache audio files locally.
 * Guarantees: "पुन्हा ऐका" (listen again) NEVER triggers a second network call.
 */

import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import type { AudioSource } from './types';

// Default cache directory for local runs / pregeneration
const DEFAULT_CACHE_DIR = path.resolve(process.cwd(), 'app/src/voice/audioCache');

/**
 * Computes a deterministic SHA-256 hash of the input text string.
 */
export function hashText(text: string): string {
  return crypto.createHash('sha256').update(text.trim()).digest('hex');
}

/**
 * Returns the expected cache file path for a given text snippet.
 */
export function getCacheFilePath(text: string, cacheDir = DEFAULT_CACHE_DIR): string {
  const hash = hashText(text);
  return path.join(cacheDir, `${hash}.wav`);
}

/**
 * Checks whether audio for this text is already present in cache.
 */
export function isAudioCached(text: string, cacheDir = DEFAULT_CACHE_DIR): boolean {
  const filePath = getCacheFilePath(text, cacheDir);
  return fs.existsSync(filePath);
}

/**
 * Saves base64 audio data into the cache for a given text snippet.
 */
export function saveAudioToCache(text: string, base64Data: string, cacheDir = DEFAULT_CACHE_DIR): string {
  if (!fs.existsSync(cacheDir)) {
    fs.mkdirSync(cacheDir, { recursive: true });
  }
  const filePath = getCacheFilePath(text, cacheDir);
  const buffer = Buffer.from(base64Data, 'base64');
  fs.writeFileSync(filePath, buffer);
  return filePath;
}

/**
 * Reads cached audio for text if available.
 */
export function getCachedAudio(text: string, cacheDir = DEFAULT_CACHE_DIR): AudioSource | null {
  const filePath = getCacheFilePath(text, cacheDir);
  if (fs.existsSync(filePath)) {
    const buffer = fs.readFileSync(filePath);
    return {
      uri: `file://${filePath}`,
      base64: buffer.toString('base64'),
      isLocalFile: true,
    };
  }
  return null;
}

/**
 * High-level helper: returns cached audio if available, or invokes the synthesizer
 * on first generation and caches the result.
 */
export async function getOrGenerateAudio(
  text: string,
  synthesizer: (text: string) => Promise<AudioSource>,
  cacheDir = DEFAULT_CACHE_DIR
): Promise<AudioSource> {
  const cached = getCachedAudio(text, cacheDir);
  if (cached) {
    return cached; // Hit cache — NO API CALL
  }

  // First-ever generation: call TTS API
  const fresh = await synthesizer(text);

  if (fresh.base64) {
    const savedPath = saveAudioToCache(text, fresh.base64, cacheDir);
    return {
      uri: `file://${savedPath}`,
      base64: fresh.base64,
      isLocalFile: true,
    };
  }

  return fresh;
}
