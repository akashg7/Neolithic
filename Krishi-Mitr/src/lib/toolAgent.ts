/**
 * Chat replies from live backend tools, with no language model in between.
 *
 * Keywords pick a tool; the tool returns facts; fixed sentences in the
 * farmer's language state them. Nothing here can invent a number: if the
 * backend has no data, the reply says so. Reply language is the app language.
 */
import { translate } from './i18n';
import { formatNumber, formatPaise } from './money';
import { STATIC_CROPS, STATIC_MANDIS } from './staticMarketData';
import { getMarketOverview, getPriceSeries, runAgentTool, AgentToolResult } from './api';
import type { AgentCard, AgentChatRequest, AgentChatResponse, AgentIntent } from './agentTypes';
import type { Locale } from '../types/api';

const has = (s: string, w: string[]) => w.some(x => s.includes(x));
const ALIASES: Record<string, string[]> = {
  Onion: ['onion', 'kanda', 'pyaz', 'pyaaz', 'कांद', 'कांदा', 'प्याज', 'प्याज़'],
  Soyabean: ['soya', 'सोया'], Cotton: ['cotton', 'kapas', 'कापूस', 'कापस', 'कपास'], Wheat: ['wheat', 'gehu', 'गहू', 'गव्ह', 'गेहू', 'गेहूँ'],
  Tomato: ['tomato', 'टोमॅटो', 'टोमैटो', 'टमाटर'], 'Bengal Gram': ['gram', 'chana', 'हरभर', 'चना', 'चने'],
  Maize: ['maize', 'corn', 'मका', 'मक्क'], 'Green Chilli': ['chilli', 'mirch', 'मिरच', 'मिर्च'], Turmeric: ['turmeric', 'haldi', 'हळद', 'हळदी', 'हल्दी'],
  Groundnut: ['groundnut', 'peanut', 'भुईमूग', 'भुईमुग', 'मूंगफली'], Pomegranate: ['pomegranate', 'डाळिंब', 'अनार'],
  Grapes: ['grape', 'द्राक्ष', 'अंगूर'], Sugarcane: ['sugarcane', 'ऊस', 'उस ', 'गन्ना', 'गन्ने'], Potato: ['potato', 'aloo', 'बटाट', 'आलू'],
};
function findCrop(m: string) { return Object.keys(ALIASES).find(k => has(m, ALIASES[k]!)); }
function findMandi(m: string) {
  return STATIC_MANDIS.find(x => {
    const stem = x.name_mr.split(' ')[0]!.slice(0, 5);
    return m.includes(x.name.split(' ')[0]!.toLowerCase()) || m.includes(stem) || m.includes(x.name_hi.split(' ')[0]!.slice(0, 5));
  })?.name;
}
function findQty(m: string): { quantity: number; unit: string } | null {
  const ascii = m.replace(/[०-९]/g, d => String('०१२३४५६७८९'.indexOf(d)));
  const hit = ascii.match(/(\d+(?:\.\d+)?)\s*(kg|kilo|किलो|quintal|qtl|क्विंटल|क्विं|bori|bag|बोरी|बोर|गोणी|goni|ton|टन)/);
  if (!hit) return null;
  const u = hit[2]!;
  const unit = /kg|kilo|किलो/.test(u) ? 'kg' : /q|क्विं/.test(u) ? 'quintal' : /ton|टन/.test(u) ? 'ton' : 'bori';
  return { quantity: Number(hit[1]), unit };
}

const FAQ: [string, string[]][] = [
  ['help_a_worst_case', ['worst', 'वाईट', 'बुरी']],
  ['help_a_no_advice', ['no advice', 'सल्ला का', 'सलाह क्यों', 'why']],
  ['help_a_grade', ['grade', 'ग्रेड', 'दर्जा', 'प्रत']],
  ['help_a_pledge', ['loan', 'pledge', 'कर्ज', 'ऋण', 'तारण']],
  ['help_a_escrow', ['escrow', 'एस्क्रो', 'एस्को', 'money safe', 'पैसे सुरक्षित']],
  ['help_a_pool', ['pool', 'पूल']],
  ['help_a_counter', ['counter', 'bargain', 'घासाघीस', 'मोलभाव']],
];

export async function toolAgentReply(req: AgentChatRequest): Promise<AgentChatResponse> {
  const l = req.locale;
  const m = ` ${req.message.toLowerCase()} `;
  const p = (mr: string, hi: string, en: string) => (l === 'mr' ? mr : l === 'hi' ? hi : en);
  const rs = (v: number | null | undefined) => formatPaise(v ?? 0, l);
  const screen = { ...req.screen_context } as unknown as Record<string, string | null>;
  const crop = findCrop(m), mandi = findMandi(m), qty = findQty(m);
  const args: Record<string, unknown> = { ...(crop ? { crop } : {}), ...(mandi ? { mandi } : {}) };
  // Name a crop and the mandi on screen may not trade it, but it is still the farmer's market.
  const run = (name: string, extra: Record<string, unknown> = {}) => runAgentTool(name, { ...args, ...extra }, l, screen);

  const sourceName = (x: string) =>
    /ARCHIVE|AGMARKNET$|MSAMB/.test(x) ? p('अ‍ॅगमार्कनेट संग्रह', 'एगमार्कनेट संग्रह', 'Agmarknet archive')
    : p('कृषी मित्र अंदाज मॉडेल', 'कृषि मित्र अनुमान मॉडल', 'Krishi Mitr forecast model');
  const reply = (intent: AgentIntent, text: string, r?: AgentToolResult | null, cards: AgentCard[] = [], quick: string[] = []): AgentChatResponse => ({
    session_id: req.session_id, transcript: null, audio_base64: null, intent_detected: intent, reply_text: text, cards, quick_replies: quick,
    ui_action: r?.ui_action ? { type: 'OFFER_NAVIGATION', target_screen: r.ui_action.target_screen, cta_label: r.ui_action.cta_label, params: r.ui_action.params } : null,
    citations: r?.citation ? [{ source: r.citation.source, title: sourceName(r.citation.source) + (r.citation.as_of ? `, ${r.citation.as_of}` : '') }] : [],
  });
  const cropLabel = (en?: string, mr?: string) => {
    const c = STATIC_CROPS.find(x => x.name === en);
    return l === 'en' ? en ?? '' : l === 'hi' ? c?.name_hi ?? mr ?? en ?? '' : mr ?? c?.name_mr ?? en ?? '';
  };
  const askWhen = p('कधी विकू?', 'कब बेचूँ?', 'When should I sell?');
  const askPrice = p('आजचा भाव काय?', 'आज का भाव क्या है?', 'What is today’s rate?');
  const failed = (r: AgentToolResult) => {
    const code = r.error?.code;
    if (code === 'NEEDS_INPUT' || code === 'AMBIGUOUS') return reply('UNKNOWN', p('कोणते पीक आणि कोणता बाजार ते सांगा.', 'कौन सी फसल और कौन सी मंडी, बताइए।', 'Tell me which crop and which market.'), null, [], []);
    return reply('UNKNOWN', p('या पिकाची या बाजारातली अलीकडची माहिती माझ्याकडे नाही, त्यामुळे अंदाज सांगत नाही. दुसरा बाजार विचारून पहा.', 'इस फसल का इस मंडी का हाल का डेटा मेरे पास नहीं है, इसलिए अंदाज़ा नहीं बताऊँगा। दूसरी मंडी पूछें।', 'I have no recent data for this crop in this market, so I won’t guess. Try another market.'), null, [], [askPrice]);
  };

  // The market on screen may not trade this crop. /market/overview picks the
  // nearest one that does; every reply names the market, so the swap is visible.
  const elsewhere = async (tool: string, extra: Record<string, unknown> = {}) => {
    try {
      const o = await getMarketOverview(crop!, mandi ?? screen.active_market_id ?? '');
      return await runAgentTool(tool, { crop, mandi: o.market.name, ...extra }, l, screen);
    } catch { return null; }
  };

  // 1. Creating a lot
  if (has(m, ['lot', 'लॉट', 'नोंद', 'list my', 'विकायच', 'बेचना है'])) {
    const r = await run('draft_lot', qty ?? {});
    if (!r.ok) return failed(r);
    const d = r.data;
    return reply('CREATE_LOT', p('ही माहिती बरोबर आहे का पहा. पुढच्या पायरीवर लॉट पूर्ण करा.', 'यह जानकारी सही है या नहीं देखें। अगले चरण में लॉट पूरा करें।', 'Check these details, then finish the lot on the next step.'), { ...r, ui_action: null },
      [{ type: 'LOT_DRAFT', data: { commodity: d.commodity?.name ?? crop ?? '', mandi: d.market?.name ?? '', quantity_kg: d.quantity_kg ?? 0 } }]);
  }

  // 2. When to sell (before price: "भाव कधी वाढेल" is a timing question)
  if (has(m, ['when', 'wait', 'hold', 'sell', 'कधी', 'थांब', 'कब', 'रुक', 'विकू', 'बेचूँ', 'बेचू', 'सल्ला', 'सलाह'])) {
    if (!has(m, ['सल्ला का', 'सलाह क्यों'])) {
      let r = await run('get_sale_window', qty ?? {});
      if (!r.ok && crop) r = (await elsewhere('get_sale_window', qty ?? {})) ?? r;
      if (!r.ok) return failed(r);
      const d = r.data, c = cropLabel(d.inputs?.commodity?.name, d.inputs?.commodity?.name_mr);
      const mk = l === 'en' ? String(d.inputs?.market?.name ?? '').replace(' APMC', '') : d.inputs?.market?.name_mr ?? '';
      const days = formatNumber(d.hold_days ?? 14, l);
      const text =
        d.action === 'NO_ADVICE' ? p(`${c}: भावात फार चढ-उतार आहे, म्हणून आज सल्ला देत नाही.`, `${c}: भाव में बहुत उतार-चढ़ाव है, इसलिए आज सलाह नहीं दूँगा।`, `${c}: rates are swinging too much, so I won’t advise today.`)
        : d.action === 'SPLIT' ? p(`${c}, ${mk}: अर्धे आज विका, अर्धे ${days} दिवस ठेवा. नफा होऊ शकतो, पण तोट्याचाही धोका आहे.`, `${c}, ${mk}: आधा आज बेचें, आधा ${days} दिन रखें। लाभ हो सकता है, पर नुकसान का जोखिम भी है।`, `${c} at ${mk}: sell half today and keep half for ${days} days. There may be a gain, but there is a risk of loss too.`)
        : d.action === 'HOLD' ? p(`${c}, ${mk}: ${days} दिवस थांबा.`, `${c}, ${mk}: ${days} दिन रुकें।`, `${c} at ${mk}: wait ${days} days.`)
        : p(`${c}, ${mk}: आजच विका. थांबून फायदा दिसत नाही.`, `${c}, ${mk}: आज ही बेचें। रुकने में फायदा नहीं दिखता।`, `${c} at ${mk}: sell today. Waiting doesn’t look worth it.`);
      return reply('SALE_WINDOW', text, r, [{
        type: 'WINDOW_VERDICT',
        data: {
          action: d.action === 'SELL_NOW' ? 'SELL' : d.action, hold_days: d.hold_days ?? undefined,
          expected_gain_paise: d.expected_gain_paise ?? undefined, worst_case_paise: d.worst_case_paise ?? undefined,
          uncertainty_pct: d.band_width_bps != null ? Math.round(d.band_width_bps / 100) : undefined,
          commodity: d.inputs?.commodity?.name ?? '', mandi: d.inputs?.market?.name ?? '', quantity_kg: d.inputs?.quantity_kg ?? 0,
        },
      }], [p('सर्वात वाईट स्थिती म्हणजे काय?', 'सबसे बुरी स्थिति क्या है?', 'What does worst case mean?'), askPrice]);
    }
  }

  // 3. Today's rate
  if (has(m, ['price', 'rate', 'भाव', 'दर ', 'दर?', 'bhav']) || (crop && m.trim().split(/\s+/).length <= 3)) {
    let r = await run('get_mandi_price');
    if (!r.ok && crop) r = (await elsewhere('get_mandi_price')) ?? r;
    if (!r.ok) return failed(r);
    const d = r.data;
    const series = await getPriceSeries(d.commodity.slug, d.market.slug, 14).then(x => x.points.map(q => q.modal_paise_per_qtl)).catch(() => [] as number[]);
    const c = cropLabel(d.commodity.name, d.commodity.name_mr);
    const mk = l === 'en' ? d.market.name.replace(' APMC', '') : d.market.name_mr;
    const ch = d.change_paise_per_qtl as number | null;
    const move = ch == null ? '' : ch >= 0
      ? p(` आठवड्यात ${rs(ch)} वाढला.`, ` हफ्ते में ${rs(ch)} बढ़ा।`, ` Up ${rs(ch)} in a week.`)
      : p(` आठवड्यात ${rs(-ch)} घटला.`, ` हफ्ते में ${rs(-ch)} घटा।`, ` Down ${rs(-ch)} in a week.`);
    return reply('CHECK_PRICE', p(`${mk}: ${c} ${rs(d.modal_paise_per_qtl)} प्रति क्विंटल.${move}`, `${mk}: ${c} ${rs(d.modal_paise_per_qtl)} प्रति क्विंटल।${move}`, `${c} at ${mk} is ${rs(d.modal_paise_per_qtl)} per quintal.${move}`), r, [{
      type: 'PRICE_SNAPSHOT',
      data: { commodity: d.commodity.name, mandi: d.market.name, modal_price_paise_per_qtl: d.modal_paise_per_qtl, series_paise_per_qtl: series, source: d.source, change_bps: d.change_bps, obs_date: d.obs_date },
    }], [askWhen]);
  }

  // 4. Checked answers about the app
  const faq = FAQ.find(([, w]) => has(m, w));
  if (faq) return reply('KNOWLEDGE', translate(faq[0], l as Locale), null, [], [askWhen, askPrice]);

  return reply('UNKNOWN',
    p('मी भाव, विकण्याची वेळ, लॉट आणि या ॲपबद्दल सांगू शकतो. औषध-फवारणीचा सल्ला देत नाही.', 'मैं भाव, बेचने का समय, लॉट और इस ऐप के बारे में बता सकता हूँ। दवा-छिड़काव की सलाह नहीं देता।', 'I can tell you rates, when to sell, help with a lot, and explain this app. I don’t advise on sprays or chemicals.'),
    null, [], [askPrice, askWhen]);
}
