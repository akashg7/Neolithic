/**
 * Test live Sarvam TTS and ASR integrations using configured key
 */

import { synthesizeMarathiSpeech } from './sarvamTTS';
import { transcribeMarathiSpeech } from './sarvamASR';
import { parseLotCreationSpeech } from './lotCreationParser';

async function testLiveSarvam() {
  console.log('--- Testing Live Sarvam Bulbul:v3 and Saaras:v3 ---');

  const textToSpeak = 'कांदा बारा क्विंटल लासलगाव';
  console.log(`1. Synthesizing: "${textToSpeak}" via Bulbul v3...`);

  const ttsResult = await synthesizeMarathiSpeech(textToSpeak);
  if (!ttsResult.base64) {
    throw new Error('TTS returned no base64 audio');
  }
  console.log(`✅ TTS Succeeded! Audio payload size: ${ttsResult.base64.length} base64 chars`);

  console.log('\n2. Transcribing back via Saaras v3...');
  const audioBuffer = Buffer.from(ttsResult.base64, 'base64');
  const asrResult = await transcribeMarathiSpeech(audioBuffer);

  console.log('✅ ASR Succeeded!');
  console.log(`  Raw Transcript: "${asrResult.raw_transcript}"`);
  console.log(`  Confidence:     ${asrResult.confidence}`);

  console.log('\n3. Testing Lot Creation Parser on live transcript...');
  const parsed = parseLotCreationSpeech(asrResult.raw_transcript, asrResult.confidence);
  console.log('  Parsed Fields:', JSON.stringify(parsed, null, 2));

  if (parsed.commodity_id !== 'onion') {
    throw new Error(`Expected commodity_id "onion", got "${parsed.commodity_id}"`);
  }
  if (parsed.qty_kg !== 1200) {
    throw new Error(`Expected qty_kg 1200, got ${parsed.qty_kg}`);
  }
  if (parsed.market_id !== 'lasalgaon') {
    throw new Error(`Expected market_id "lasalgaon", got "${parsed.market_id}"`);
  }

  console.log('✅ Live Sarvam round-trip + field extraction PASSED 100%!');
}

testLiveSarvam().catch((err) => {
  console.error('❌ Live Sarvam Test Failed:', err);
  process.exit(1);
});
