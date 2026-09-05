/**
 * Unit tests for textTemplates.ts
 * Tests all 5 actions and 4 refusal reasons using fixtures.
 */

import { verdictSentence, refusalSentence, pledgeSentence, worstCaseSentence, REFUSAL_MR } from './textTemplates';
import type { WindowRes, PledgeQuote } from './types';
import mockWindowRes from './__fixtures__/mockWindowRes.json';
import mockPledgeQuote from './__fixtures__/mockPledgeQuote.json';

function runTemplateTests() {
  console.log('--- Testing textTemplates.ts ---');

  // 1. Test HOLD verdict
  const holdRes = mockWindowRes.hold_verdict as unknown as WindowRes;
  const holdSpeech = verdictSentence(holdRes);
  const expectedHold = 'पुढे पाच दिवस थांबा. तुम्हाला ₹पंचेचाळीस हजार रुपये जास्त मिळू शकतात.';
  if (holdSpeech !== expectedHold) {
    console.error(`❌ FAIL HOLD sentence:\n  Expected: "${expectedHold}"\n  Actual:   "${holdSpeech}"`);
    process.exit(1);
  }
  console.log('✅ HOLD verdict sentence matches exactly.');

  // 2. Test Worst Case sentence
  const riskSpeech = worstCaseSentence(holdRes.worst_case_paise);
  const expectedRisk = 'वाईट परिस्थितीत ₹बारा हजार रुपये तोटा होऊ शकतो.';
  if (riskSpeech !== expectedRisk) {
    console.error(`❌ FAIL Worst Case sentence:\n  Expected: "${expectedRisk}"\n  Actual:   "${riskSpeech}"`);
    process.exit(1);
  }
  console.log('✅ Worst case sentence matches exactly.');

  // 3. Test SPLIT verdict
  const splitRes = mockWindowRes.split_verdict as unknown as WindowRes;
  const splitSpeech = verdictSentence(splitRes);
  const expectedSplit = 'अर्धा माल आजच विका, अर्धा सात दिवस थांबवा.';
  if (splitSpeech !== expectedSplit) {
    console.error(`❌ FAIL SPLIT sentence:\n  Expected: "${expectedSplit}"\n  Actual:   "${splitSpeech}"`);
    process.exit(1);
  }
  console.log('✅ SPLIT verdict sentence matches exactly.');

  // 4. Test SELL_NOW verdict
  const sellNowRes = mockWindowRes.sell_now_verdict as unknown as WindowRes;
  const sellNowSpeech = verdictSentence(sellNowRes);
  const expectedSellNow = 'आजच विका. थांबण्याचा फायदा नाही.';
  if (sellNowSpeech !== expectedSellNow) {
    console.error(`❌ FAIL SELL_NOW sentence:\n  Expected: "${expectedSellNow}"\n  Actual:   "${sellNowSpeech}"`);
    process.exit(1);
  }
  console.log('✅ SELL_NOW verdict sentence matches exactly.');

  // 5. Test SELL_ELSEWHERE verdict
  const sellElsewhereRes = mockWindowRes.sell_elsewhere_verdict as unknown as WindowRes;
  const sellElsewhereSpeech = verdictSentence(sellElsewhereRes);
  const expectedSellElsewhere = 'जवळच्या दुसऱ्या बाजारात विका, तिथे जास्त भाव मिळेल.';
  if (sellElsewhereSpeech !== expectedSellElsewhere) {
    console.error(`❌ FAIL SELL_ELSEWHERE sentence:\n  Expected: "${expectedSellElsewhere}"\n  Actual:   "${sellElsewhereSpeech}"`);
    process.exit(1);
  }
  console.log('✅ SELL_ELSEWHERE verdict sentence matches exactly.');

  // 6. Test all 4 NO_ADVICE Refusal reasons
  const refusalKeys = [
    'BAND_TOO_WIDE',
    'INSUFFICIENT_HISTORY',
    'STALE_DATA',
    'GAIN_BELOW_COST',
  ] as const;

  for (const reason of refusalKeys) {
    const speech = refusalSentence(reason);
    if (speech !== REFUSAL_MR[reason]) {
      console.error(`❌ FAIL Refusal reason ${reason}`);
      process.exit(1);
    }
  }
  console.log('✅ All 4 NO_ADVICE refusal sentences match verbatim CANON strings.');

  // 7. Test Pledge sentence
  const pledgeData = mockPledgeQuote.standard_quote as unknown as PledgeQuote;
  const pledgeSpeech = pledgeSentence(pledgeData);
  const expectedPledge = '₹एक लाख रुपये आज मिळतील. तीस दिवसांचे व्याज ₹दोन हजार पाचशे रुपये. एकूण परतफेड ₹एक लाख दोन हजार पाचशे रुपये.';
  if (pledgeSpeech !== expectedPledge) {
    console.error(`❌ FAIL Pledge sentence:\n  Expected: "${expectedPledge}"\n  Actual:   "${pledgeSpeech}"`);
    process.exit(1);
  }
  console.log('✅ Pledge sentence matches expected Marathi phrasing.');

  console.log('\n🎉 ALL TEXT TEMPLATE TESTS PASSED!');
}

runTemplateTests();
