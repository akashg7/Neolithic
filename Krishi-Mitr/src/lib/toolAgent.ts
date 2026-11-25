/**
 * Chat replies from live backend tools, with no language model in between.
 *
 * Keywords pick a tool; the tool returns facts; fixed sentences in the
 * farmer's language state them. Nothing here can invent a number: if the
 * backend has no data, the reply says so. Reply language is the app language.
 */
import { translate } from './i18n';
import { formatNumber, formatPaise } from './money';
import { parseFarmerDetails } from './parseFarmerDetails';
import { STATIC_CROPS, STATIC_DISTRICTS, STATIC_MANDIS } from './staticMarketData';
import { getDistricts, getLots, getMarketOverview, getOffers, getPriceSeries, getTransactions, refLabel, runAgentTool, AgentToolResult } from './api';
import type { AgentCard, AgentChatRequest, AgentChatResponse, AgentIntent } from './agentTypes';
import type { Locale } from '../types/api';

const has = (s: string, w: string[]) => w.some(x => s.includes(x));
const ALIASES: Record<string, string[]> = {
  Onion: ['onion', 'kanda', 'pyaz', 'pyaaz', 'कांद', 'कांदा', 'प्याज', 'प्याज़'],
  Soyabean: ['soya', 'सोया'], Cotton: ['cotton', 'kapas', 'कापूस', 'कापस', 'कपास'], Wheat: ['wheat', 'gehu', 'गहू', 'गव्ह', 'गेहू', 'गेहूँ'],
  Tomato: ['tomato', 'टोमॅटो', 'टोमैटो', 'टमाटर'], 'Bengal Gram': ['gram', 'chana', 'harbhara', 'हरभर', 'हरभऱ', 'हरबर', 'चना', 'चने', 'चण'],
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

const MEMO = new Map<string, { crop?: string; mandi?: string; awaitingQty?: boolean }>();

export async function toolAgentReply(req: AgentChatRequest): Promise<AgentChatResponse> {
  const l = req.locale;
  const m = ` ${req.message.toLowerCase()} `;
  const p = (mr: string, hi: string, en: string) => (l === 'mr' ? mr : l === 'hi' ? hi : en);
  const rs = (v: number | null | undefined) => formatPaise(v ?? 0, l);
  const screen = { ...req.screen_context } as unknown as Record<string, string | null>;
  // Short memory per conversation: a follow-up like "20 quintal" or "and at
  // Pimpalgaon?" keeps the crop/mandi already named, and finishes a timing
  // question that was only waiting for the quantity.
  const prev = MEMO.get(req.session_id) ?? {};
  const qty = findQty(m);
  const crop = findCrop(m) ?? prev.crop, mandi = findMandi(m) ?? prev.mandi;
  const followUpQty = !!qty && !!prev.awaitingQty && !findCrop(m);
  MEMO.set(req.session_id, { crop, mandi });
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
    // Ask for exactly what the server said is missing (e.g. only the quantity).
    const missing = ((r.error as { missing?: string[] } | undefined)?.missing ?? []).map(x => x.toLowerCase());
    if (code === 'NEEDS_INPUT' && missing.length && missing.every(x => x.includes('quantity') || x.includes('qty')))
      return (MEMO.set(req.session_id, { crop, mandi, awaitingQty: true }), reply('UNKNOWN', p('किती क्विंटल आहे ते सांगा, उदा. "२० क्विंटल".', 'कितने क्विंटल हैं, बताइए, जैसे "20 क्विंटल"।', 'How many quintals do you have? For example, "20 quintal".'), null, [], []));
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

  // A one-tap button to the screen that shows the full list.
  const goto = (target_screen: string, cta_label: string) =>
    ({ ok: true, data: {}, ui_action: { target_screen, cta_label } } as unknown as AgentToolResult);
  // "Show my lots" asks what he has; anything with a quantity or "list/add/new"
  // is a new lot and goes to the draft below.
  const isLotQuestion = has(m, ['my lot', 'my produce', 'माझे लॉट', 'माझा माल', 'मेरे लॉट', 'मेरा माल', 'show my', 'how many lot'])
    && !qty && !has(m, ['list my lot:', 'list a', 'new lot', 'add', 'create', 'नवीन', 'नया', 'विकायच', 'बेचना']);

  const isChem = has(m, ['pesticide', 'insecticide', 'fungicide', 'herbicide', 'weedicide', 'chemical', 'dosage', 'spray dose', 'कीटकनाशक', 'बुरशीनाशक', 'तणनाशक', 'फवारणी', 'कीटनाशक', 'दवा', 'छिड़काव']);
  if (isChem) {
    return reply('OUT_OF_SCOPE', p(
      'कीटकनाशके किंवा रसायनांच्या मात्रेबाबत मी सल्ला देऊ शकत नाही. कृपया यासाठी तुमच्या जवळच्या कृषी विज्ञान केंद्राशी (KVK) संपर्क साधा.',
      'मैं कीटनाशकों या रसायनों की मात्रा पर सलाह नहीं दे सकता। कृपया इसके लिए अपने नज़दीकी कृषि विज्ञान केंद्र (KVK) से संपर्क करें।',
      'I can’t advise on pesticides or chemical doses. Please contact your nearest Krishi Vigyan Kendra (KVK) for this.',
    ), null, [], [askPrice, askWhen]);
  }

  // -1. Onboarding profile helper on Auth / Profile screens
  const onbScreen = /^(S0_Splash|S1_Language|S2_Phone|S0?3_Profile)$/.test(screen.current_screen || '');
  if (onbScreen) {
    const districts = await getDistricts().catch(() =>
      STATIC_DISTRICTS.map((d, idx) => ({ id: `dist_${idx + 1}`, name: d.name, name_mr: d.name_mr })),
    );
    const parsed = parseFarmerDetails(req.message, districts);
    if (parsed.name || parsed.districtId || parsed.village) {
      const dist = districts.find(d => d.id === parsed.districtId);
      const profileCard: AgentCard = {
        type: 'ONBOARD_PROFILE',
        data: {
          name: parsed.name,
          village: parsed.village,
          district_id: parsed.districtId,
          district_name: dist ? (l === 'en' ? dist.name : dist.name_mr) : null,
        },
      };
      const ui: AgentToolResult = {
        ok: true,
        tool: 'extract_onboarding_profile',
        data: profileCard.data as Record<string, any>,
        ui_action: {
          type: 'PREFILL',
          target_screen: 'S3_Profile',
          cta_label: p('फॉर्ममध्ये भरा', 'फ़ॉर्म में भरें', 'Fill profile'),
          params: {
            ...(parsed.districtId ? { district_id: parsed.districtId } : {}),
            ...(parsed.name ? { name: parsed.name } : {}),
            ...(parsed.village ? { village: parsed.village } : {}),
          },
        },
      };
      return reply(
        'ONBOARD',
        p('तुमचा तपशील वाचला आहे. खालील बटण दाबून फॉर्ममध्ये भरा.', 'आपकी जानकारी समझ ली गई है। नीचे बटन दबाकर फ़ॉर्म भरें।', 'Got your profile details. Tap below to fill them into the form.'),
        ui,
        [profileCard],
      );
    }
  }

  // 0a. His offers (buyer bids waiting on him)
  if (has(m, ['offer', 'bid', 'बोली', 'ऑफर', 'खरेदीदार', 'खरीदार', 'buyer'])) {
    const offers = await getOffers().catch(() => null);
    if (!offers) return failed({ ok: false } as AgentToolResult);
    const waiting = offers.filter(o => o.status === 'OPEN' && o.initiator !== 'FARMER')
      .sort((a, b) => b.price_paise_per_qtl - a.price_paise_per_qtl);
    const withBuyer = offers.filter(o => o.status === 'OPEN' && o.initiator === 'FARMER').length;
    const best = waiting[0];
    const text = best
      ? p(`${formatNumber(waiting.length, l)} बोली तुमच्या उत्तराची वाट पाहत आहेत. सर्वात जास्त ${rs(best.price_paise_per_qtl)} प्रति क्विंटल.`,
          `${formatNumber(waiting.length, l)} बोली आपके जवाब का इंतज़ार कर रही हैं। सबसे ऊँची ${rs(best.price_paise_per_qtl)} प्रति क्विंटल।`,
          `${waiting.length} ${waiting.length === 1 ? 'offer is' : 'offers are'} waiting for your reply. The best is ${rs(best.price_paise_per_qtl)} per quintal.`)
      : withBuyer
        ? p('नवी बोली नाही. तुमचे उत्तर खरेदीदाराकडे आहे.', 'कोई नई बोली नहीं। आपका जवाब खरीदार के पास है।', 'No new offers. Your reply is with the buyer.')
        : p('सध्या कोणतीही बोली नाही.', 'अभी कोई बोली नहीं है।', 'You have no offers right now.');
    return reply('MY_OFFERS', text, goto('S37_Talks', p('बोली पहा', 'बोलियाँ देखें', 'See offers')), [], [askPrice]);
  }

  // 0b. His deals (escrow progress)
  if (has(m, ['deal', 'payment', 'paid', 'money', 'सौदा', 'सौदे', 'पैसे', 'पैसा', 'भुगतान', 'escrow'])) {
    const txs = await getTransactions().catch(() => null);
    if (!txs) return failed({ ok: false } as AgentToolResult);
    const STAGE: Record<string, [string, string, string]> = {
      CREATED: ['करार झाला', 'सौदा तय', 'agreed'], ESCROW_HELD: ['पैसे सुरक्षित ठेवले', 'पैसा सुरक्षित रखा', 'money held'],
      DISPATCHED: ['माल रवाना', 'माल रवाना', 'dispatched'], DELIVERED: ['माल पोहोचला', 'माल पहुँचा', 'delivered'],
      INSPECTED: ['तपासणी झाली', 'जाँच हुई', 'inspected'], RELEASED: ['पैसे मिळाले', 'भुगतान हो गया', 'paid out'],
      SETTLED: ['पैसे मिळाले', 'भुगतान हो गया', 'paid out'], DISPUTED: ['तक्रार चालू', 'शिकायत जारी', 'in dispute'],
    };
    const stage = (st: string) => { const x = STAGE[st] ?? [st, st, st.toLowerCase()]; return p(x[0], x[1], x[2]); };
    const live = txs.filter(t => !['RELEASED', 'SETTLED', 'REFUNDED'].includes(t.status));
    const text = !txs.length
      ? p('अजून कोणताही सौदा नाही.', 'अभी कोई सौदा नहीं है।', 'You have no deals yet.')
      : live.length
        ? p(`${formatNumber(live.length, l)} सौदे चालू: `, `${formatNumber(live.length, l)} सौदे चालू: `, `${live.length} ${live.length === 1 ? 'deal' : 'deals'} in progress: `)
          + live.map(t => `${formatNumber(Math.round(t.qty_kg / 100), l)} ${p('क्विंटल', 'क्विंटल', 'qtl')} @ ${rs(t.price_paise_per_qtl)} — ${stage(t.status)}`).join('; ') + '.'
        : p('सर्व सौदे पूर्ण झाले, पैसे मिळाले.', 'सभी सौदे पूरे, भुगतान हो गया।', 'All your deals are complete and paid.');
    return reply('MY_DEALS', text, goto('S31_DealsList', p('सौदे पहा', 'सौदे देखें', 'See deals')), [], [askPrice]);
  }

  // 0c. His lots (a question about what he has, not "list a new lot")
  if (isLotQuestion) {
    const lots = await getLots().catch(() => null);
    if (!lots) return failed({ ok: false } as AgentToolResult);
    const kg = lots.reduce((a, x) => a + x.qty_kg, 0);
    const names = [...new Set(lots.map(x => refLabel(x.commodity_id, l as Locale)))].join(', ');
    const text = lots.length
      ? p(`तुमचे ${formatNumber(lots.length, l)} लॉट, एकूण ${formatNumber(Math.round(kg / 100), l)} क्विंटल: ${names}.`,
          `आपके ${formatNumber(lots.length, l)} लॉट, कुल ${formatNumber(Math.round(kg / 100), l)} क्विंटल: ${names}।`,
          `You have ${lots.length} ${lots.length === 1 ? 'lot' : 'lots'}, ${Math.round(kg / 100)} quintals in all: ${names}.`)
      : p('अजून एकही लॉट नाही.', 'अभी कोई लॉट नहीं है।', 'You have no lots yet.');
    return reply('MY_LOTS', text, goto('S15_MyLots', p('माझा माल पहा', 'मेरा माल देखें', 'See my produce')), [], [askPrice]);
  }

  // 0d. Best nearby mandi (net of transport), from /market/overview's ranking
  if (has(m, ['nearby', 'best mandi', 'best market', 'which mandi', 'which market', 'कोणत्या बाजार', 'जवळच', 'कौन सी मंडी', 'पास की मंडी', 'सबसे अच्छी मंडी'])) {
    const c = crop ?? STATIC_CROPS[0]!.name;
    try {
      const o = await getMarketOverview(c, mandi ?? screen.active_market_id ?? 'Lasalgaon APMC');
      const rows = o.nearby.rows.slice(0, 3);
      if (!rows.length) return failed({ ok: false } as AgentToolResult);
      const name = (r: (typeof rows)[number]) => (l === 'en' ? String((r as { name?: string }).name ?? r.name_mr).replace(' APMC', '') : r.name_mr);
      const top = rows[0]!;
      const cl = cropLabel(o.commodity.name, o.commodity.name_mr);
      const list = rows.map(r => `${name(r)} ${rs(r.net_paise_per_qtl)}`).join(', ');
      return reply('NEARBY_MANDIS',
        p(`${cl}: वाहतूक वजा करून सर्वात चांगला भाव ${name(top)} — ${rs(top.net_paise_per_qtl)} प्रति क्विंटल. (${list})`,
          `${cl}: ढुलाई घटाकर सबसे अच्छा भाव ${name(top)} — ${rs(top.net_paise_per_qtl)} प्रति क्विंटल। (${list})`,
          `${cl}: after transport, ${name(top)} pays most — ${rs(top.net_paise_per_qtl)} per quintal. (${list})`),
        goto('PricesIndex', p('सर्व बाजार पहा', 'सभी मंडियाँ देखें', 'See all markets')), [], [askWhen]);
    } catch { return failed({ ok: false } as AgentToolResult); }
  }

  // 1. Creating a lot
  if (has(m, ['lot', 'लॉट', 'नोंद', 'list my', 'विकायच', 'बेचना है'])) {
    const r = await run('draft_lot', qty ?? {});
    if (!r.ok) return failed(r);
    const d = r.data;
    return reply('CREATE_LOT', p('ही माहिती बरोबर आहे का पहा. पुढच्या पायरीवर लॉट पूर्ण करा.', 'यह जानकारी सही है या नहीं देखें। अगले चरण में लॉट पूरा करें।', 'Check these details, then finish the lot on the next step.'), { ...r, ui_action: null },
      [{ type: 'LOT_DRAFT', data: { commodity: d.commodity?.name ?? crop ?? '', mandi: d.market?.name ?? '', quantity_kg: d.quantity_kg ?? 0, ...(d.commodity?.slug ? { commodity_id: d.commodity.slug } : {}), ...(d.market?.slug ? { market_id: d.market.slug } : {}) } }]);
  }

  // 2. When to sell (before price: "भाव कधी वाढेल" is a timing question)
  if (followUpQty || has(m, ['when', 'wait', 'hold', 'sell', 'कधी', 'थांब', 'कब', 'रुक', 'विकू', 'बेचूँ', 'बेचू', 'सल्ला', 'सलाह'])) {
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
        : d.action === 'SELL_ELSEWHERE' ? p(`${c}: दुसऱ्या बाजारात विकणे जास्त फायदेशीर दिसेल.`, `${c}: दूसरी मंडी में बेचना ज़्यादा फ़ायदेमंद दिखता है।`, `${c}: selling at another nearby mandi nets more after transport.`)
        : p(`${c}, ${mk}: आजच विका. थांबून फायदा दिसत नाही.`, `${c}, ${mk}: आज ही बेचें। रुकने में फायदा नहीं दिखता।`, `${c} at ${mk}: sell today. Waiting doesn’t look worth it.`);
      return reply('SALE_WINDOW', text, r, [{
        type: 'WINDOW_VERDICT',
        data: {
          action: d.action === 'SELL_NOW' ? 'SELL' : d.action, hold_days: d.hold_days ?? undefined,
          expected_gain_paise: d.expected_gain_paise ?? undefined, worst_case_paise: d.worst_case_paise ?? undefined,
          uncertainty_pct: d.band_width_bps != null ? Math.round(d.band_width_bps / 100) : undefined,
          commodity: d.inputs?.commodity?.name ?? '', mandi: d.inputs?.market?.name ?? '', quantity_kg: d.inputs?.quantity_kg ?? 0,
          alt_market: d.alt_market ?? null,
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

  // 4. Checked answers about the app + live RAG knowledge base lookup
  const faq = FAQ.find(([, w]) => has(m, w));
  if (faq) return reply('KNOWLEDGE', translate(faq[0], l as Locale), null, [], [askWhen, askPrice]);

  const query = req.message.trim();
  if (query.length >= 2) {
    try {
      const rag = await runAgentTool('search_agri_knowledge', { query, ...(crop ? { crop } : {}) }, l, screen);
      const chunks = Array.isArray(rag.data?.chunks) ? rag.data.chunks : [];
      if (rag.ok && chunks.length > 0) {
        const top = chunks[0] as { text?: string; section_title?: string; source_doc?: string; chunk_id?: string };
        const ragCard: AgentCard = {
          type: 'RAG_CITATION',
          data: {
            query,
            chunks: chunks.map((ch: any) => ({
              chunk_id: String(ch.chunk_id || ''),
              source_doc: String(ch.source_doc || ''),
              section_title: ch.section_title ? String(ch.section_title) : undefined,
              category: ch.category ? String(ch.category) : undefined,
              score: typeof ch.score === 'number' ? ch.score : undefined,
              snippet: String(ch.text ?? ch.snippet ?? '').slice(0, 240),
            })),
          },
        };
        return {
          ...reply('RAG', String(top.text || ''), rag, [ragCard], [askWhen, askPrice]),
          citations: chunks.slice(0, 2).map((ch: any) => ({
            source: String(ch.source_doc || 'krishi_kb'),
            title: String(ch.section_title || ch.source_doc || 'Krishi Mitr KB'),
            chunk_id: ch.chunk_id ? String(ch.chunk_id) : null,
            section_title: ch.section_title ? String(ch.section_title) : null,
          })),
        };
      }
    } catch {
      /* fall through to general help message */
    }
  }

  return reply('UNKNOWN',
    p('मी भाव, विकण्याची वेळ, लॉट आणि या ॲपबद्दल सांगू शकतो. औषध-फवारणीचा सल्ला देत नाही.', 'मैं भाव, बेचने का समय, लॉट और इस ऐप के बारे में बता सकता हूँ। दवा-छिड़काव की सलाह नहीं देता।', 'I can tell you rates, when to sell, help with a lot, and explain this app. I don’t advise on sprays or chemicals.'),
    null, [], [askPrice, askWhen]);
}
