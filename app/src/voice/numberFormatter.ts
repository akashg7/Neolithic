/**
 * Mandi-Setu Voice Module — Number Formatter (Track A: Voice-OUT)
 * Converts integer paise, quantities, and numbers into spoken Marathi phrases
 * using Indian numbering system (lakh/hazaar/she).
 */

import { MARATHI_0_TO_99, MARATHI_HUNDREDS, MARATHI_SCALES } from './numberWords';

/**
 * Converts paise to integer rupee amount.
 * As per project invariant I1 and canon doc: gain_paise from the decision engine
 * is already the total gain for the entire lot.
 */
export function paiseToRupeeAmountForQty(paise: number | null | undefined, _qtyKg?: number): number {
  if (paise == null) return 0;
  return Math.round(paise / 100);
}

/**
 * Converts an integer into Marathi number words using Indian grouping.
 * Examples:
 *   0 -> "शून्य"
 *   11 -> "अकरा"
 *   100 -> "शंभर"
 *   1428 -> "एक हजार चारशे अठ्ठावीस"
 *   62900 -> "बासष्ट हजार नऊशे"
 *   100000 -> "एक लाख"
 *   250000 -> "दोन लाख पन्नास हजार"
 */
export function spokenNumber(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '';
  n = Math.floor(n);

  if (n === 0) {
    return MARATHI_0_TO_99[0];
  }

  if (n < 0) {
    return `उणे ${spokenNumber(Math.abs(n))}`;
  }

  if (n < 100) {
    return MARATHI_0_TO_99[n];
  }

  const parts: string[] = [];

  // 1. Crores (कोटी = 1,00,00,000)
  const crore = Math.floor(n / 10000000);
  let rem = n % 10000000;
  if (crore > 0) {
    parts.push(`${spokenNumber(crore)} ${MARATHI_SCALES.CRORE}`);
  }

  // 2. Lakhs (लाख = 1,00,000)
  const lakh = Math.floor(rem / 100000);
  rem = rem % 100000;
  if (lakh > 0) {
    parts.push(`${spokenNumber(lakh)} ${MARATHI_SCALES.LAKH}`);
  }

  // 3. Thousands (हजार = 1,000)
  const thousand = Math.floor(rem / 1000);
  rem = rem % 1000;
  if (thousand > 0) {
    parts.push(`${spokenNumber(thousand)} ${MARATHI_SCALES.THOUSAND}`);
  }

  // 4. Hundreds (शे / शंभर = 100)
  const hundred = Math.floor(rem / 100);
  const remHundred = rem % 100;

  if (hundred > 0) {
    if (hundred === 1) {
      if (remHundred === 0 && parts.length === 0) {
        // standalone 100
        parts.push(MARATHI_SCALES.HUNDRED);
      } else {
        parts.push('एकशे');
      }
    } else {
      parts.push(MARATHI_HUNDREDS[hundred * 100] || `${spokenNumber(hundred)}शे`);
    }
  }

  // 5. Tens & Units (0 - 99)
  if (remHundred > 0) {
    parts.push(MARATHI_0_TO_99[remHundred]);
  }

  return parts.join(' ').trim();
}

/**
 * Formats a rupee amount as spoken Marathi with currency symbol and word.
 * Example: 62900 -> "₹बासष्ट हजार नऊशे रुपये"
 */
export function spokenRupees(rupees: number | null | undefined): string {
  const val = Math.abs(rupees ?? 0);
  const words = spokenNumber(val);
  return `₹${words} रुपये`;
}

/**
 * Formats duration in days into spoken Marathi.
 * Example: 5 -> "५ दिवस" / "पाच दिवस"
 */
export function spokenDays(days: number | null | undefined): string {
  if (days == null) return '';
  return `${spokenNumber(days)} दिवस`;
}
