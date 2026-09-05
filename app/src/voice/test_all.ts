/**
 * Master Verification Suite for Mandi-Setu Voice Module
 * Runs all unit and integration tests across Phase 0, Track A, and Track B.
 */

import { execSync } from 'child_process';

const testSuites = [
  { name: 'Phase 0 — Shared Contract & Fixtures', file: 'app/src/voice/test_phase0.ts' },
  { name: 'Track A — Number Formatter (Marathi Words & Scales)', file: 'app/src/voice/test_numberFormatter.ts' },
  { name: 'Track A — Text Templates (Verdict, Refusal, Pledge)', file: 'app/src/voice/test_textTemplates.ts' },
  { name: 'Track A — Audio Cache & Fallback Ladder', file: 'app/src/voice/test_cache_and_fallback.ts' },
  { name: 'Track B — Number Parser (Reverse Marathi Words -> Int)', file: 'app/src/voice/test_numberParser.ts' },
  { name: 'Track B — Lot Creation & Registration Slot Fill', file: 'app/src/voice/test_trackB.ts' },
  { name: 'Live Sarvam — Bulbul:v3 & Saaras:v3 Live Round-Trip', file: 'app/src/voice/test_sarvam_live.ts' },
];

console.log('========================================================');
console.log('  MANDI-SETU VOICE MODULE — FULL VERIFICATION RUN');
console.log('========================================================\n');

let passedCount = 0;

for (const suite of testSuites) {
  console.log(`\n▶️ Running: ${suite.name}`);
  console.log(`   File: ${suite.file}`);
  try {
    const output = execSync(`npx -y tsx ${suite.file}`, {
      stdio: 'pipe',
      encoding: 'utf-8',
    });
    console.log(output.trim());
    console.log(`✅ ${suite.name} PASSED!`);
    passedCount++;
  } catch (err: any) {
    console.error(`❌ ${suite.name} FAILED:`);
    console.error(err.stdout || err.stderr || err.message);
    process.exit(1);
  }
}

console.log('\n========================================================');
console.log(`  ALL ${passedCount}/${testSuites.length} TEST SUITES PASSED SUCCESSFULLY!`);
console.log('========================================================\n');
