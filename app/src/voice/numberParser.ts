/**
 * Mandi-Setu Voice Module — Number Parser (Track B: Voice-IN)
 * Converts spoken Marathi number words, Devanagari numerals, and Indian scale terms
 * back into standard integers. Inverse of numberFormatter.spokenNumber().
 */

import { WORD_TO_NUMBER_MAP, DEVANAGARI_DIGITS, MARATHI_SCALES } from './numberWords';

/**
 * Converts Devanagari digits (०-९) to ASCII digits (0-9)
 */
export function devanagariToAsciiDigits(text: string): string {
  let result = text;
  DEVANAGARI_DIGITS.forEach((devDigit, idx) => {
    result = result.split(devDigit).join(String(idx));
  });
  return result;
}

/**
 * Checks if a string consists entirely of digits (Devanagari or ASCII)
 */
function isNumericString(text: string): boolean {
  const ascii = devanagariToAsciiDigits(text.trim());
  return /^\d+$/.test(ascii);
}

/**
 * Recursively parses a sequence of Marathi number tokens into an integer
 */
function parseTokenList(tokens: string[]): number | null {
  if (tokens.length === 0) return null;

  // Check if single token is a direct number or digit
  if (tokens.length === 1) {
    const single = tokens[0];
    if (isNumericString(single)) {
      return parseInt(devanagariToAsciiDigits(single), 10);
    }
    if (WORD_TO_NUMBER_MAP[single] !== undefined) {
      return WORD_TO_NUMBER_MAP[single];
    }
  }

  // Handle Crores (कोटी)
  const croreIdx = tokens.indexOf(MARATHI_SCALES.CRORE);
  if (croreIdx !== -1) {
    const leftTokens = tokens.slice(0, croreIdx);
    const rightTokens = tokens.slice(croreIdx + 1);
    const leftVal = leftTokens.length > 0 ? (parseTokenList(leftTokens) ?? 1) : 1;
    const rightVal = rightTokens.length > 0 ? (parseTokenList(rightTokens) ?? 0) : 0;
    return leftVal * 10000000 + rightVal;
  }

  // Handle Lakhs (लाख)
  const lakhIdx = tokens.indexOf(MARATHI_SCALES.LAKH);
  if (lakhIdx !== -1) {
    const leftTokens = tokens.slice(0, lakhIdx);
    const rightTokens = tokens.slice(lakhIdx + 1);
    const leftVal = leftTokens.length > 0 ? (parseTokenList(leftTokens) ?? 1) : 1;
    const rightVal = rightTokens.length > 0 ? (parseTokenList(rightTokens) ?? 0) : 0;
    return leftVal * 100000 + rightVal;
  }

  // Handle Thousands (हजार)
  const thousandIdx = tokens.indexOf(MARATHI_SCALES.THOUSAND);
  if (thousandIdx !== -1) {
    const leftTokens = tokens.slice(0, thousandIdx);
    const rightTokens = tokens.slice(thousandIdx + 1);
    const leftVal = leftTokens.length > 0 ? (parseTokenList(leftTokens) ?? 1) : 1;
    const rightVal = rightTokens.length > 0 ? (parseTokenList(rightTokens) ?? 0) : 0;
    return leftVal * 1000 + rightVal;
  }

  // Handle sub-thousand: hundreds (शे, शंभर) + 0-99
  let total = 0;
  let matchedAny = false;

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    if (isNumericString(token)) {
      total += parseInt(devanagariToAsciiDigits(token), 10);
      matchedAny = true;
      continue;
    }

    // Check for "शे" suffix directly or as separate word (e.g. "चार शे")
    if (token === MARATHI_SCALES.SHE && i > 0) {
      const prevVal = WORD_TO_NUMBER_MAP[tokens[i - 1]];
      if (prevVal !== undefined && prevVal < 10) {
        total += prevVal * 100 - prevVal; // adjust previous addition
        matchedAny = true;
        continue;
      }
    }

    const val = WORD_TO_NUMBER_MAP[token];
    if (val !== undefined) {
      total += val;
      matchedAny = true;
    }
  }

  return matchedAny ? total : null;
}

/**
 * Cleans input text and parses any spoken Marathi number phrase or numeral
 * into an integer.
 * Examples:
 *   "बारा" -> 12
 *   "१२" -> 12
 *   "बासष्ट हजार नऊशे" -> 62900
 *   "दोन लाख पन्नास हजार" -> 250000
 */
export function parseMarathiNumber(text: string | null | undefined): number | null {
  if (!text) return null;

  // Clean string: remove common punctuation and symbols
  const cleaned = text
    .replace(/[,\.।?!]/g, ' ')
    .trim();

  // If directly digits
  if (isNumericString(cleaned)) {
    return parseInt(devanagariToAsciiDigits(cleaned), 10);
  }

  const tokens = cleaned
    .split(/\s+/)
    .filter((t) => t.length > 0);

  if (tokens.length === 0) return null;

  return parseTokenList(tokens);
}

/**
 * Extracts a quantity in kg from Marathi speech phrase.
 * Understands units like "क्विंटल" (1 quintal = 100 kg), "किलो" (1 kg), "टन" (1000 kg).
 * Example:
 *   "बारा क्विंटल" -> 1200
 *   "पन्नास किलो" -> 50
 */
export function parseQuantityKg(phrase: string): { qty_kg: number | null; confidence: number } {
  if (!phrase) return { qty_kg: null, confidence: 0 };

  const lower = phrase.toLowerCase();
  let multiplier = 1; // default kg
  let unitConfidence = 0.8;

  if (lower.includes('क्विंटल') || lower.includes('quintel') || lower.includes('quintal')) {
    multiplier = 100;
    unitConfidence = 0.95;
  } else if (lower.includes('टन') || lower.includes('ton')) {
    multiplier = 1000;
    unitConfidence = 0.95;
  } else if (lower.includes('किलो') || lower.includes('kg')) {
    multiplier = 1;
    unitConfidence = 0.95;
  }

  // Remove unit words before parsing number
  const numText = phrase
    .replace(/क्विंटल|quintel|quintal|टन|ton|किलो|kg/gi, ' ')
    .trim();

  const num = parseMarathiNumber(numText);
  if (num == null) {
    return { qty_kg: null, confidence: 0 };
  }

  return {
    qty_kg: num * multiplier,
    confidence: unitConfidence,
  };
}
