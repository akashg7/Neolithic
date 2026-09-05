/**
 * Mandi-Setu Voice Module — Text Templates (Track A: Voice-OUT)
 * Generates natural, spoken Marathi sentences from structured decision engine data.
 * Rule: refusal sentences are locked, verbatim strings (CANON AI architecture).
 */

import type { WindowRes, PledgeQuote, RefusalReason } from './types';
import { spokenNumber, spokenRupees, paiseToRupeeAmountForQty } from './numberFormatter';

/**
 * Locked Marathi refusal statements from Canon AI Architecture doc.
 * Do not regenerate dynamically.
 */
export const REFUSAL_MR: Record<RefusalReason, string> = {
  BAND_TOO_WIDE: 'पुढील १४ दिवसांचा अंदाज खूप अनिश्चित आहे. चुकीचा सल्ला देण्यापेक्षा आम्ही सांगत नाही. आजचा भाव पाहून तुम्ही ठरवा.',
  INSUFFICIENT_HISTORY: 'या बाजारासाठी पुरेशी जुनी माहिती नाही. आम्ही अंदाज देऊ शकत नाही.',
  STALE_DATA: 'या बाजाराची ताजी माहिती उपलब्ध नाही. जुन्या भावावर सल्ला देणे धोक्याचे आहे.',
  GAIN_BELOW_COST: 'थांबून मिळणारा फायदा खर्चापेक्षा कमी आहे. थांबण्यात अर्थ नाही.',
};

/**
 * Returns exact Marathi sentence for a refusal reason
 */
export function refusalSentence(reason: RefusalReason | string): string {
  const key = reason as RefusalReason;
  return REFUSAL_MR[key] || 'सध्या या मालावर सल्ला उपलब्ध नाही.';
}

/**
 * Generates spoken Marathi sentence for decision window recommendation (S9)
 */
export function verdictSentence(res: WindowRes, qtyKg?: number): string {
  switch (res.action) {
    case 'HOLD': {
      const rupees = paiseToRupeeAmountForQty(res.expected_gain_paise, qtyKg);
      const amount = spokenRupees(rupees);
      const days = spokenNumber(res.hold_days ?? 0);
      return `पुढे ${days} दिवस थांबा. तुम्हाला ${amount} जास्त मिळू शकतात.`;
    }
    case 'SPLIT': {
      const days = spokenNumber(res.hold_days ?? 0);
      return `अर्धा माल आजच विका, अर्धा ${days} दिवस थांबवा.`;
    }
    case 'SELL_NOW':
      return 'आजच विका. थांबण्याचा फायदा नाही.';
    case 'SELL_ELSEWHERE':
      return 'जवळच्या दुसऱ्या बाजारात विका, तिथे जास्त भाव मिळेल.';
    case 'NO_ADVICE':
      return refusalSentence(res.refusal_reason || 'BAND_TOO_WIDE');
    default:
      return 'सध्या कोणताही सल्ला उपलब्ध नाही.';
  }
}

/**
 * Generates spoken Marathi sentence for pledge card quote (S11)
 */
export function pledgeSentence(pledge: PledgeQuote): string {
  const loanRupees = paiseToRupeeAmountForQty(pledge.loan_paise);
  const interestRupees = paiseToRupeeAmountForQty(pledge.interest_paise);
  const totalRupees = paiseToRupeeAmountForQty(pledge.loan_paise + pledge.interest_paise);

  const loan = spokenRupees(loanRupees);
  const interest = spokenRupees(interestRupees);
  const total = spokenRupees(totalRupees);
  const days = spokenNumber(pledge.days);

  return `${loan} आज मिळतील. ${days} दिवसांचे व्याज ${interest}. एकूण परतफेड ${total}.`;
}

/**
 * Generates spoken Marathi sentence for downside / worst-case risk (S9)
 */
export function worstCaseSentence(worstCasePaise: number | null | undefined, qtyKg?: number): string {
  if (worstCasePaise == null || worstCasePaise === 0) return '';
  const lossRupees = paiseToRupeeAmountForQty(Math.abs(worstCasePaise), qtyKg);
  const amount = spokenRupees(lossRupees);
  return `वाईट परिस्थितीत ${amount} तोटा होऊ शकतो.`;
}

/**
 * Combines verdict sentence and downside risk sentence for S9 speech output
 */
export function fullVerdictSentence(res: WindowRes, qtyKg?: number): string {
  const main = verdictSentence(res, qtyKg);
  if (res.action === 'HOLD' && res.worst_case_paise && res.worst_case_paise < 0) {
    const risk = worstCaseSentence(res.worst_case_paise, qtyKg);
    return `${main} ${risk}`;
  }
  return main;
}
