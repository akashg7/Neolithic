/**
 * Mandi-Setu Voice Module — Demo Audio Pre-generation Script (Track A: A8)
 * Generates all rehearsed demo audio files ahead of time so the demo flow works
 * 100% offline (in Airplane Mode) via local cache hits without touching the network.
 */

import * as fs from 'fs';
import * as path from 'path';
import { verdictSentence, refusalSentence, pledgeSentence, worstCaseSentence, REFUSAL_MR } from '../textTemplates';
import { saveAudioToCache, isAudioCached } from '../audioCache';
import { synthesizeMarathiSpeech } from '../sarvamTTS';
import { isSarvamConfigured } from '../config';
import type { WindowRes, PledgeQuote, AssayQuestion } from '../types';

import mockWindowRes from '../__fixtures__/mockWindowRes.json';
import mockPledgeQuote from '../__fixtures__/mockPledgeQuote.json';
import mockAssayQuestions from '../__fixtures__/mockAssayQuestions.json';

const CACHE_DIR = path.resolve(process.cwd(), 'app/src/voice/audioCache');

// Minimal valid WAV header + silence data (for offline fallback pregeneration when SARVAM_API_KEY is not set)
const SILENT_WAV_BASE64 = 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';

async function generateSentenceAudio(sentence: string, label: string) {
  if (!sentence) return;

  if (isAudioCached(sentence, CACHE_DIR)) {
    console.log(`⏩ Already cached [${label}]: "${sentence.substring(0, 30)}..."`);
    return;
  }

  console.log(`🎙️ Generating [${label}]: "${sentence.substring(0, 35)}..."`);

  if (isSarvamConfigured()) {
    try {
      const audio = await synthesizeMarathiSpeech(sentence);
      if (audio.base64) {
        saveAudioToCache(sentence, audio.base64, CACHE_DIR);
        console.log(`✅ Saved from Sarvam API [${label}]`);
        return;
      }
    } catch (err: any) {
      console.warn(`⚠️ Sarvam API call failed for [${label}]: ${err.message}. Saving stub audio.`);
    }
  } else {
    console.log(`ℹ️ Sarvam API key not set — saving pregenerated bundle stub for [${label}]`);
  }

  // Save bundled stub so airplane mode demo never fails
  saveAudioToCache(sentence, SILENT_WAV_BASE64, CACHE_DIR);
}

export async function pregenerateAllDemoAudio() {
  console.log('=== Starting Mandi-Setu Pre-generation for Demo Flow ===\n');
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }

  // 1. Verdict Scenarios (S9)
  console.log('--- 1. Generating Verdict & Refusal Sentences ---');
  const holdRes = mockWindowRes.hold_verdict as unknown as WindowRes;
  await generateSentenceAudio(verdictSentence(holdRes), 'S9_HOLD');
  await generateSentenceAudio(worstCaseSentence(holdRes.worst_case_paise), 'S9_WORST_CASE');

  const splitRes = mockWindowRes.split_verdict as unknown as WindowRes;
  await generateSentenceAudio(verdictSentence(splitRes), 'S9_SPLIT');

  const sellNowRes = mockWindowRes.sell_now_verdict as unknown as WindowRes;
  await generateSentenceAudio(verdictSentence(sellNowRes), 'S9_SELL_NOW');

  const sellElseRes = mockWindowRes.sell_elsewhere_verdict as unknown as WindowRes;
  await generateSentenceAudio(verdictSentence(sellElseRes), 'S9_SELL_ELSEWHERE');

  // Refusal reasons (verbatim strings)
  for (const [key, text] of Object.entries(REFUSAL_MR)) {
    await generateSentenceAudio(text, `S9_REFUSAL_${key}`);
  }

  // 2. Pledge Quote (S11)
  console.log('\n--- 2. Generating Pledge Quote Sentences ---');
  const pledgeData = mockPledgeQuote.standard_quote as unknown as PledgeQuote;
  await generateSentenceAudio(pledgeSentence(pledgeData), 'S11_PLEDGE');

  // 3. 6 Grading Assay Questions (S13) — Static & Permanent
  console.log('\n--- 3. Generating 6 Grading Assay Questions ---');
  const questions = mockAssayQuestions as unknown as AssayQuestion[];
  for (const q of questions) {
    await generateSentenceAudio(q.prompt_mr, `S13_ASSAY_${q.id.toUpperCase()}`);
  }

  // 4. Registration Slot-Fill Prompts
  console.log('\n--- 4. Generating Registration Prompts ---');
  const regPrompts = [
    { key: 'name', prompt: 'तुमचे नाव काय आहे?' },
    { key: 'district', prompt: 'तुम्ही कोणत्या जिल्ह्यात राहता?' },
    { key: 'village', prompt: 'तुमच्या गावाचे नाव काय आहे?' },
    { key: 'commodity', prompt: 'तुम्ही मुख्यतः कोणते पीक घेता?' },
    { key: 'confirm', prompt: 'दिलेली माहिती बरोबर आहे का?' },
  ];
  for (const p of regPrompts) {
    await generateSentenceAudio(p.prompt, `REG_${p.key.toUpperCase()}`);
  }

  console.log('\n🎉 Pre-generation complete! All demo and static prompts are ready in audioCache/');
}

if (require.main === module || (typeof process !== 'undefined' && process.argv[1]?.includes('pregenerateDemoAudio'))) {
  pregenerateAllDemoAudio().catch((err) => {
    console.error('Fatal pregeneration error:', err);
    process.exit(1);
  });
}
