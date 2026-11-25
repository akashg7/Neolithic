/**
 * Screen-aware starter prompts. Keyed by route name; the chat drawer shows the
 * entry for whatever the farmer is looking at, falling back to `default`.
 */
import type { Locale } from '../types/api';

type L3 = Record<Locale, string>;

const DEFAULT: L3[] = [
  { mr: 'कांदा कधी विकू?', hi: 'प्याज कब बेचूँ?', en: 'When should I sell my onion?' },
  { mr: 'कांद्याचा आजचा भाव काय?', hi: 'प्याज का आज का भाव क्या है?', en: 'What is today\'s onion price?' },
  { mr: '५०० किलो कांद्याचा लॉट तयार करा', hi: '500 किलो प्याज का लॉट बनाओ', en: 'Create a lot for 500 kg onion' },
  { mr: 'एस्क्रो म्हणजे काय?', hi: 'एस्क्रो क्या है?', en: 'What is escrow?' },
];

const BY_SCREEN: Record<string, L3[]> = {
  S9_Verdict: [
    { mr: 'थांबण्याचा सल्ला का दिला?', hi: 'रुकने की सलाह क्यों दी?', en: 'Why this advice?' },
    { mr: 'सर्वात वाईट परिस्थिती म्हणजे काय?', hi: 'सबसे बुरी स्थिति क्या है?', en: 'What is the worst case?' },
    { mr: 'पिक कर्ज मिळेल का?', hi: 'क्या फसल ऋण मिलेगा?', en: 'Can I get a pledge loan?' },
  ],
  S20_QualityDiagnostic: [
    { mr: 'ग्रेड A कसा मिळवायचा?', hi: 'ग्रेड A कैसे मिलेगा?', en: 'How do I get Grade A?' },
    { mr: 'ओलावा किती असावा?', hi: 'नमी कितनी होनी चाहिए?', en: 'How much moisture is allowed?' },
  ],
  S15_MyLots: [
    { mr: '५०० किलो कांद्याचा लॉट तयार करा', hi: '500 किलो प्याज का लॉट बनाओ', en: 'Create a lot for 500 kg onion' },
    { mr: 'पूल म्हणजे काय?', hi: 'पूल क्या है?', en: 'What is pooling?' },
  ],
  PricesIndex: [
    { mr: 'कांद्याचा आजचा भाव काय?', hi: 'प्याज का आज का भाव क्या है?', en: 'What is today\'s onion price?' },
    { mr: 'टोमॅटो कधी विकू?', hi: 'टमाटर कब बेचूँ?', en: 'When should I sell tomato?' },
  ],
  S3_Profile: [
    { mr: 'माझं नाव रामभाऊ पाटील, गाव निफाड, जिल्हा नाशिक', hi: 'मेरा नाम रामभाऊ पाटिल, गाँव निफाड़, ज़िला नासिक', en: 'My name is Rambhau Patil, village Niphad, district Nashik' },
  ],
  S03_Profile: [
    { mr: 'माझं नाव रामभाऊ पाटील, गाव निफाड, जिल्हा नाशिक', hi: 'मेरा नाम रामभाऊ पाटिल, गाँव निफाड़, ज़िला नासिक', en: 'My name is Rambhau Patil, village Niphad, district Nashik' },
  ],
};

export function promptsFor(screen: string, locale: Locale): string[] {
  return (BY_SCREEN[screen] ?? DEFAULT).map(p => p[locale] ?? p.mr);
}
