/**
 * Unit tests for numberParser.ts (Track B: Voice-IN)
 */

import { parseMarathiNumber, parseQuantityKg, devanagariToAsciiDigits } from './numberParser';
import { spokenNumber } from './numberFormatter';

const testPairs: [string, number][] = [
  ['शून्य', 0],
  ['एक', 1],
  ['नऊ', 9],
  ['दहा', 10],
  ['अकरा', 11],
  ['बारा', 12],
  ['एकोणीस', 19],
  ['वीस', 20],
  ['पंचेचाळीस', 45],
  ['शंभर', 100],
  ['नऊशे नव्व्याण्णव', 999],
  ['एक हजार', 1000],
  ['एक हजार चारशे अठ्ठावीस', 1428],
  ['पंचेचाळीस हजार', 45000],
  ['बासष्ट हजार नऊशे', 62900],
  ['एक लाख', 100000],
  ['दोन लाख पन्नास हजार', 250000],
  ['१२', 12],
  ['१२००', 1200],
  ['४५०००', 45000],
];

function runParserTests() {
  console.log('--- Testing numberParser.parseMarathiNumber ---');
  let passed = 0;
  for (const [text, expected] of testPairs) {
    const actual = parseMarathiNumber(text);
    if (actual !== expected) {
      console.error(`❌ FAIL: parseMarathiNumber("${text}")\n  Expected: ${expected}\n  Actual:   ${actual}`);
      process.exit(1);
    } else {
      passed++;
    }
  }
  console.log(`✅ All ${passed} numberParser test cases passed!`);

  // Test round-trip identity: spokenNumber -> parseMarathiNumber
  console.log('\n--- Testing Round-Trip: spokenNumber -> parseMarathiNumber ---');
  const roundTripValues = [0, 1, 12, 45, 100, 1428, 45000, 62900, 100000, 250000];
  for (const val of roundTripValues) {
    const words = spokenNumber(val);
    const parsed = parseMarathiNumber(words);
    if (parsed !== val) {
      console.error(`❌ FAIL Round-trip for ${val}: words="${words}", parsed=${parsed}`);
      process.exit(1);
    }
  }
  console.log('✅ Round-trip test passed for all values!');

  // Test quantity parser
  console.log('\n--- Testing parseQuantityKg ---');
  const qtyTests: [string, number][] = [
    ['बारा क्विंटल', 1200],
    ['पन्नास क्विंटल', 5000],
    ['१० क्विंटल', 1000],
    ['२५ किलो', 25],
    ['२ टन', 2000],
  ];

  for (const [phrase, expectedKg] of qtyTests) {
    const res = parseQuantityKg(phrase);
    if (res.qty_kg !== expectedKg) {
      console.error(`❌ FAIL parseQuantityKg("${phrase}"): expected ${expectedKg}, got ${res.qty_kg}`);
      process.exit(1);
    }
  }
  console.log('✅ parseQuantityKg passed for all unit combinations!');

  console.log('\n🎉 ALL NUMBER PARSER TESTS PASSED!');
}

runParserTests();
