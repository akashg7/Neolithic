/**
 * Unit tests for numberFormatter.ts
 * Required test values from handoff §5.4
 */

import { spokenNumber, spokenRupees, paiseToRupeeAmountForQty } from './numberFormatter';

const testCases: [number, string][] = [
  [0, 'शून्य'],
  [1, 'एक'],
  [9, 'नऊ'],
  [10, 'दहा'],
  [11, 'अकरा'],
  [19, 'एकोणीस'],
  [20, 'वीस'],
  [45, 'पंचेचाळीस'],
  [100, 'शंभर'],
  [999, 'नऊशे नव्व्याण्णव'],
  [1000, 'एक हजार'],
  [1428, 'एक हजार चारशे अठ्ठावीस'],
  [45000, 'पंचेचाळीस हजार'],
  [62900, 'बासष्ट हजार नऊशे'],
  [100000, 'एक लाख'],
  [250000, 'दोन लाख पन्नास हजार'],
];

function runTests() {
  console.log('--- Testing numberFormatter.spokenNumber ---');
  let passed = 0;
  for (const [input, expected] of testCases) {
    const actual = spokenNumber(input);
    if (actual !== expected) {
      console.error(`❌ FAIL: spokenNumber(${input})\n  Expected: "${expected}"\n  Actual:   "${actual}"`);
      process.exit(1);
    } else {
      passed++;
    }
  }
  console.log(`✅ All ${passed} spokenNumber test cases passed successfully!`);

  console.log('\n--- Testing spokenRupees ---');
  const rupeeStr = spokenRupees(62900);
  const expectedRupeeStr = '₹बासष्ट हजार नऊशे रुपये';
  if (rupeeStr !== expectedRupeeStr) {
    console.error(`❌ FAIL: spokenRupees(62900)\n  Expected: "${expectedRupeeStr}"\n  Actual:   "${rupeeStr}"`);
    process.exit(1);
  }
  console.log(`✅ spokenRupees(62900) matches "${expectedRupeeStr}"`);

  console.log('\n--- Testing paiseToRupeeAmountForQty ---');
  if (paiseToRupeeAmountForQty(4500000) !== 45000) {
    console.error('❌ FAIL: paiseToRupeeAmountForQty(4500000) should be 45000');
    process.exit(1);
  }
  console.log('✅ paiseToRupeeAmountForQty passed!');

  console.log('\n🎉 ALL NUMBER FORMATTER TESTS PASSED!');
}

runTests();
