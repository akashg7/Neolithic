/**
 * Offline stand-in for `POST /agent/chat`, shaped exactly like Contract 1.
 * Keyword routing only — this exists so the whole chat UI (cards, deep links,
 * refusal, citations) can be built and demoed before Member 5's agent ships.
 * Every number here is fixture data, never a real forecast.
 */
import type { Locale } from '../types/api';
import type { AgentChatRequest, AgentChatResponse } from './agentTypes';

type L3 = Record<Locale, string>;
const pick = (l: Locale, v: L3) => v[l] ?? v.mr;

const has = (s: string, words: string[]) => words.some(w => s.includes(w));

export async function mockAgentReply(req: AgentChatRequest): Promise<AgentChatResponse> {
  await new Promise(r => setTimeout(r, 1100 + Math.random() * 700));
  const m = req.message.toLowerCase();
  const l = req.locale;
  const base = {
    session_id: req.session_id,
    transcript: null,
    audio_base64: null,
    ui_action: null,
    citations: [],
    cards: [],
  };

  // Refusal path — the engine's NO_ADVICE gate, shown honestly.
  if (has(m, ['tomato', 'टोमॅटो', 'टमाटर'])) {
    return {
      ...base,
      intent_detected: 'SALE_WINDOW',
      reply_text: pick(l, {
        mr: 'सध्या पिंपळगाव बाजारात टोमॅटोच्या भावात खूप चढ-उतार आहे. धोका जास्त असल्याने थांबण्याचा सल्ला मी देऊ शकत नाही. आजचा भाव पाहून तुम्ही स्वतः ठरवा.',
        hi: 'अभी पिंपळगाव मंडी में टमाटर के भाव में बहुत उतार-चढ़ाव है। जोखिम ज्यादा होने से मैं रुकने की सलाह नहीं दे सकता। आज का भाव देखकर खुद तय करें।',
        en: 'Tomato prices at Pimpalgaon are swinging too widely right now. I cannot advise you to wait. Check today\'s rate and decide for yourself.',
      }),
      cards: [
        {
          type: 'WINDOW_VERDICT',
          data: { action: 'NO_ADVICE', uncertainty_pct: 41, commodity: 'Tomato', mandi: 'Pimpalgaon APMC', quantity_kg: 800 },
        },
      ],
      ui_action: {
        type: 'OFFER_NAVIGATION',
        target_screen: 'PricesIndex',
        cta_label: pick(l, { mr: 'आजचे भाव पहा', hi: 'आज के भाव देखें', en: 'See today\'s prices' }),
      },
      citations: [{ source: 'window_engine_v1', title: 'Refusal gate: forecast band above 35%' }],
      quick_replies: [],
    };
  }

  if (has(m, ['wait', 'कब', 'थांब', 'कधी', 'when', 'window', 'ruk', 'रुक', 'hold', 'सल्ला'])) {
    return {
      ...base,
      intent_detected: 'SALE_WINDOW',
      reply_text: pick(l, {
        mr: 'तुमच्या ५०० किलो कांद्यासाठी लासलगाव मंडीत ५ दिवस थांबण्याचा सल्ला आहे. वाहतूक व साठवणूक खर्च वजा करूनही नफा अपेक्षित आहे.',
        hi: 'आपके 500 किलो प्याज के लिए लासलगांव मंडी में 5 दिन रुकने की सलाह है। परिवहन और भंडारण खर्च घटाकर भी लाभ अपेक्षित है।',
        en: 'For your 500 kg of onion at Lasalgaon, waiting 5 days is advised. A gain is expected even after transport and storage costs.',
      }),
      cards: [
        {
          type: 'WINDOW_VERDICT',
          data: {
            action: 'HOLD',
            hold_days: 5,
            expected_gain_paise: 185000,
            worst_case_paise: 40000,
            commodity: 'Onion',
            mandi: 'Lasalgaon APMC',
            quantity_kg: 500,
          },
        },
      ],
      ui_action: {
        type: 'OFFER_NAVIGATION',
        target_screen: 'S9_Verdict',
        cta_label: pick(l, { mr: 'संपूर्ण तपशील पहा', hi: 'पूरा विवरण देखें', en: 'See full details' }),
        params: { commodity_id: 'cmd_onion', market_id: 'mkt_lasalgaon', qty_kg: 500 },
      },
      citations: [{ source: 'window_engine_v1', title: '14-day LightGBM quantile forecast' }],
      quick_replies: [
        pick(l, { mr: '५०० किलो कांद्याचा लॉट तयार करा', hi: '500 किलो प्याज का लॉट बनाओ', en: 'Create a lot for 500 kg onion' }),
        pick(l, { mr: 'पिक कर्ज मिळेल का?', hi: 'क्या फसल ऋण मिलेगा?', en: 'Can I get a pledge loan?' }),
      ],
    };
  }

  if (has(m, ['lot', 'लॉट', 'विकायचा', 'बोरी', 'quintal', 'क्विंटल'])) {
    return {
      ...base,
      intent_detected: 'CREATE_LOT',
      reply_text: pick(l, {
        mr: 'मी तुमच्यासाठी लॉटचा मसुदा तयार केला आहे. माहिती बरोबर असेल तर खाली पुष्टी करा.',
        hi: 'मैंने आपके लिए लॉट का मसौदा तैयार किया है। जानकारी सही हो तो नीचे पुष्टि करें।',
        en: 'I drafted a lot for you. If the details are right, confirm below.',
      }),
      cards: [{ type: 'LOT_DRAFT', data: { commodity: 'Onion', mandi: 'Lasalgaon APMC', quantity_kg: 500 } }],
      quick_replies: [],
    };
  }

  if (has(m, ['price', 'भाव', 'rate', 'दर'])) {
    return {
      ...base,
      intent_detected: 'CHECK_PRICE',
      reply_text: pick(l, {
        mr: 'लासलगाव मंडीत कांद्याचा आजचा भाव खाली दिला आहे. गेल्या सात दिवसांत भाव वाढत आहे.',
        hi: 'लासलगांव मंडी में प्याज का आज का भाव नीचे है। पिछले सात दिनों में भाव बढ़ रहा है।',
        en: 'Today\'s onion rate at Lasalgaon is below. Prices have been rising over the last seven days.',
      }),
      cards: [
        {
          type: 'PRICE_SNAPSHOT',
          data: {
            commodity: 'Onion',
            mandi: 'Lasalgaon APMC',
            modal_price_paise_per_qtl: 185000,
            series_paise_per_qtl: [168000, 171000, 169500, 176000, 179000, 182500, 185000],
            source: 'AGMARKNET',
          },
        },
      ],
      quick_replies: [],
    };
  }

  if (has(m, ['loan', 'कर्ज', 'ऋण', 'wdra', 'pledge', 'grade', 'ग्रेड', 'escrow', 'एस्क्रो', 'storage', 'साठव'])) {
    return {
      ...base,
      intent_detected: 'KNOWLEDGE',
      reply_text: pick(l, {
        mr: 'गोदामात माल ठेवल्यावर मिळणाऱ्या पावतीवर (e-NWR) तुम्हाला कर्ज मिळू शकते. साधारणपणे मालाच्या किमतीच्या ७०% पर्यंत रक्कम मिळते. अटी गोदामानुसार बदलतात.',
        hi: 'गोदाम में माल रखने पर मिलने वाली रसीद (e-NWR) पर आपको ऋण मिल सकता है। आमतौर पर माल की कीमत का 70% तक मिलता है। शर्तें गोदाम के अनुसार बदलती हैं।',
        en: 'You can borrow against the warehouse receipt (e-NWR) once your produce is stored. Typically up to 70% of its value. Terms vary by warehouse.',
      }),
      ui_action: {
        type: 'OFFER_NAVIGATION',
        target_screen: 'S13_CropLoan',
        cta_label: pick(l, { mr: 'कर्ज पर्याय पहा', hi: 'ऋण विकल्प देखें', en: 'See loan options' }),
      },
      citations: [
        { source: 'WDRA_Pledge_Guidelines.md', title: 'WDRA e-NWR pledge loan guidelines' },
        { source: 'NHRDF_Storage_Manual.md', title: 'NHRDF onion storage manual' },
      ],
      quick_replies: [],
    };
  }

  return {
    ...base,
    intent_detected: 'UNKNOWN',
    reply_text: pick(l, {
      mr: 'मी भाव, विक्रीची योग्य वेळ, लॉट तयार करणे आणि या ॲपबद्दल मदत करू शकतो. पिकावरील औषधांबद्दल सल्ला मी देत नाही. खालील पर्याय निवडा किंवा पुन्हा विचारा.',
      hi: 'मैं भाव, बेचने का सही समय, लॉट बनाने और इस ऐप की जानकारी में मदद कर सकता हूँ। फसल की दवाओं पर सलाह मैं नहीं देता। नीचे से चुनें या दोबारा पूछें।',
      en: 'I can help with prices, the right time to sell, creating a lot, and how this app works. I do not advise on crop chemicals. Pick an option below or ask again.',
    }),
    quick_replies: [
      pick(l, { mr: 'कांद्याचा आजचा भाव काय?', hi: 'प्याज का आज का भाव क्या है?', en: 'What is today\'s onion price?' }),
      pick(l, { mr: 'कांदा कधी विकू?', hi: 'प्याज कब बेचूँ?', en: 'When should I sell my onion?' }),
      pick(l, { mr: 'एस्क्रो म्हणजे काय?', hi: 'एस्क्रो क्या है?', en: 'What is escrow?' }),
    ],
  };
}
