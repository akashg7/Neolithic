/**
 * Verification script for Phase 0 Shared Contract Freeze
 */
import { MARATHI_0_TO_99, WORD_TO_NUMBER_MAP, MARATHI_HUNDREDS, MARATHI_SCALES } from './numberWords';
import { VOICE_CONFIG, isSarvamConfigured } from './config';
import type { WindowRes, PledgeQuote, AssayQuestion, ParsedLotFields } from './types';

// Load fixtures
import mockWindowRes from './__fixtures__/mockWindowRes.json';
import mockPledgeQuote from './__fixtures__/mockPledgeQuote.json';
import mockAssayQuestions from './__fixtures__/mockAssayQuestions.json';
import mockTranscripts from './__fixtures__/mockTranscripts.json';

function runPhase0Verification() {
  console.log('--- Starting Phase 0 Verification ---');

  // 1. Verify number words table
  console.log('1. Checking MARATHI_0_TO_99 table...');
  if (MARATHI_0_TO_99.length !== 100) {
    throw new Error(`Expected 100 entries in MARATHI_0_TO_99, found ${MARATHI_0_TO_99.length}`);
  }
  for (let i = 0; i < 100; i++) {
    const word = MARATHI_0_TO_99[i];
    if (!word || typeof word !== 'string' || word.trim().length === 0) {
      throw new Error(`Invalid entry at index ${i}`);
    }
  }
  console.log('✅ MARATHI_0_TO_99 has all 100 entries (0 to 99) populated.');

  // Check specific reference words
  const checks: [number, string][] = [
    [0, 'शून्य'],
    [1, 'एक'],
    [11, 'अकरा'],
    [12, 'बारा'],
    [20, 'वीस'],
    [45, 'पंचेचाळीस'],
    [62, 'बासष्ट'],
    [99, 'नव्व्याण्णव'],
  ];
  for (const [n, expected] of checks) {
    if (MARATHI_0_TO_99[n] !== expected) {
      throw new Error(`Expected MARATHI_0_TO_99[${n}] to be '${expected}', got '${MARATHI_0_TO_99[n]}'`);
    }
  }
  console.log('✅ Specific reference words match specification.');

  // 2. Checking Reverse Map
  console.log('2. Checking WORD_TO_NUMBER_MAP...');
  if (WORD_TO_NUMBER_MAP['शून्य'] !== 0) throw new Error('शून्य should map to 0');
  if (WORD_TO_NUMBER_MAP['बासष्ठ'] !== 62) throw new Error('बासष्ठ should map to 62');
  if (WORD_TO_NUMBER_MAP['हजार'] !== 1000) throw new Error('हजार should map to 1000');
  if (WORD_TO_NUMBER_MAP['लाख'] !== 100000) throw new Error('लाख should map to 100000');
  if (WORD_TO_NUMBER_MAP['कोटी'] !== 10000000) throw new Error('कोटी should map to 10000000');
  console.log('✅ WORD_TO_NUMBER_MAP correctly maps base and scale values.');

  // 3. Verify Config
  console.log('3. Checking VOICE_CONFIG...');
  if (VOICE_CONFIG.confidenceThreshold !== 0.6) {
    throw new Error(`Expected default threshold 0.6, got ${VOICE_CONFIG.confidenceThreshold}`);
  }
  if (VOICE_CONFIG.maxRecordingSeconds !== 10) {
    throw new Error(`Expected default max recording seconds 10, got ${VOICE_CONFIG.maxRecordingSeconds}`);
  }
  console.log('✅ Config defaults loaded properly.');

  // 4. Verify Fixtures
  console.log('4. Validating fixtures against types...');
  const holdVerdict = mockWindowRes.hold_verdict as unknown as WindowRes;
  if (holdVerdict.action !== 'HOLD' || holdVerdict.hold_days !== 5) {
    throw new Error('mockWindowRes.hold_verdict format mismatch');
  }

  const standardPledge = mockPledgeQuote.standard_quote as unknown as PledgeQuote;
  if (standardPledge.loan_paise !== 10000000 || standardPledge.days !== 30) {
    throw new Error('mockPledgeQuote.standard_quote format mismatch');
  }

  const assayList = mockAssayQuestions as unknown as AssayQuestion[];
  if (assayList.length !== 6) {
    throw new Error(`Expected 6 assay questions, got ${assayList.length}`);
  }
  const requiredAssayIds = [
    'size_uniform',
    'colour_uniform',
    'sprouting',
    'damage_pct',
    'moisture_feel',
    'foreign_matter',
  ];
  for (const id of requiredAssayIds) {
    if (!assayList.some((q) => q.id === id && q.prompt_mr.length > 0)) {
      throw new Error(`Missing or empty prompt for assay question: ${id}`);
    }
  }
  console.log('✅ All 6 assay questions validated with Marathi prompts.');

  if (!mockTranscripts.lot_creation || !mockTranscripts.registration) {
    throw new Error('mockTranscripts structure invalid');
  }
  console.log('✅ Mock transcripts structure validated.');

  console.log('--- Phase 0 Verification PASSED! ---');
}

runPhase0Verification();
