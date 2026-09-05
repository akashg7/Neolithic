/**
 * Unit tests for audioCache.ts and fallbackTTS.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { getOrGenerateAudio, hashText } from './audioCache';
import { synthesizeWithFallback } from './fallbackTTS';
import type { AudioSource } from './types';

const TEST_CACHE_DIR = path.resolve(process.cwd(), 'app/src/voice/audioCache/__test_cache__');

async function runCacheAndFallbackTests() {
  console.log('--- Testing audioCache.ts ---');

  // Clean test cache directory
  if (fs.existsSync(TEST_CACHE_DIR)) {
    fs.rmSync(TEST_CACHE_DIR, { recursive: true, force: true });
  }

  const sampleText = 'पुढे पाच दिवस थांबा. तुम्हाला ₹पंचेचाळीस हजार रुपये जास्त मिळू शकतात.';
  let mockApiCallCount = 0;

  const mockSynthesizer = async (text: string): Promise<AudioSource> => {
    mockApiCallCount++;
    return {
      uri: 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=',
      base64: 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=',
      isLocalFile: false,
    };
  };

  // 1. First call: cache MISS, should invoke synthesizer
  console.log('1. Testing first-ever generation (cache miss)...');
  const res1 = await getOrGenerateAudio(sampleText, mockSynthesizer, TEST_CACHE_DIR);
  if (mockApiCallCount !== 1) {
    throw new Error(`Expected mockApiCallCount to be 1, got ${mockApiCallCount}`);
  }
  if (!res1.isLocalFile) {
    throw new Error('Expected first generation to be saved locally');
  }
  console.log('✅ First generation succeeded and cached to disk.');

  // 2. Second call ("पुन्हा ऐका"): cache HIT, should NOT invoke synthesizer!
  console.log('2. Testing "पुन्हा ऐका" (cache hit)...');
  const res2 = await getOrGenerateAudio(sampleText, mockSynthesizer, TEST_CACHE_DIR);
  if (mockApiCallCount !== 1) {
    throw new Error(`Expected mockApiCallCount to STAY 1, but got ${mockApiCallCount}! Network call re-triggered!`);
  }
  if (res1.uri !== res2.uri) {
    throw new Error(`Cached URIs differ: ${res1.uri} vs ${res2.uri}`);
  }
  console.log('✅ Cache hit confirmed: "पुन्हा ऐका" made ZERO additional network calls!');

  // 3. Fallback ladder test
  console.log('\n--- Testing fallbackTTS.ts ladder ---');
  // Test forced fallback ladder by temporarily simulating failure
  const originalEndpoint = process.env.SARVAM_TTS_ENDPOINT;
  process.env.SARVAM_TTS_ENDPOINT = 'https://invalid-endpoint-for-test.sarvam.ai';
  const { VOICE_CONFIG } = await import('./config');
  VOICE_CONFIG.sarvamTtsEndpoint = 'https://invalid-endpoint-for-test.sarvam.ai';

  const fallbackRes = await synthesizeWithFallback('आजच विका.');
  if (!fallbackRes.uri.startsWith('device-native://')) {
    throw new Error(`Expected device-native fallback URI, got ${fallbackRes.uri}`);
  }
  console.log('✅ Fallback ladder successfully degraded to device-native speech without crashing.');

  // Restore
  VOICE_CONFIG.sarvamTtsEndpoint = 'https://api.sarvam.ai/text-to-speech';
  if (originalEndpoint) process.env.SARVAM_TTS_ENDPOINT = originalEndpoint;

  // Cleanup test cache
  if (fs.existsSync(TEST_CACHE_DIR)) {
    fs.rmSync(TEST_CACHE_DIR, { recursive: true, force: true });
  }

  console.log('\n🎉 ALL CACHE AND FALLBACK TESTS PASSED!');
}

runCacheAndFallbackTests().catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
