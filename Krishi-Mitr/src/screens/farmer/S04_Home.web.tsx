/**
 * S04 Home — website version. Same data and features as the phone screen
 * (crop/market picker, rate, history + table, spoken advice, forecast, costs,
 * nearby mandis, my lots), laid out as a page. Differences that are fixes:
 * lots come from `GET /lots` (the phone screen renders fixtures), and the
 * worst case is shown beside the gain at the same size.
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { ListenButton } from '../../components/ui/ListenButton';
import { WebFooter } from '../../components/web/WebFooter';
import { getLots } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { CropStrip, cropName, Empty, heroSrc, Ic, PlacePickers, Skel, sourceLine, useMarket, useSay, verdictOf } from '../../web/kit';
import { LotCard } from '../../web/LotCard';
import { MandiTable } from '../../web/MandiTable';
import { PriceChart } from '../../web/PriceChart';

export default function S04_Home({ navigation }: { navigation: any }) {
  const say = useSay();
  const { s, rs, n, locale, day } = say;
  const { user } = useAuth();
  const { crop, o, loading, failed, refetch } = useMarket();
  const [days, setDays] = useState<7 | 14 | 30>(14);
  const { data: lots } = useQuery({ queryKey: ['lots'], queryFn: getLots });

  const first = (user?.name ?? '').trim().split(' ')[0] ?? '';
  const title = cropName(crop, locale);
  const v = o?.verdict;
  const verdict = v ? verdictOf(v.action, v.hold_days, say) : null;
  const up = (o?.change_7d_bps ?? 0) >= 0;
  const lo = o?.min_30d_paise_per_qtl ?? 0, hi = o?.max_30d_paise_per_qtl ?? 0;
  const at = o && hi > lo ? Math.min(100, Math.max(0, ((o.latest.modal_paise_per_qtl - lo) / (hi - lo)) * 100)) : 50;
  const fc = o?.forecast.points ?? [];
  const explain = v ? (locale === 'en' ? v.explain_en : locale === 'mr' ? v.explain_mr : '') ?? '' : '';
  const costs = v?.itemised_costs ?? null;
  const COST: [string, string][] = [
    ['transport_paise_per_qtl', s('वाहतूक', 'ढुलाई', 'Transport')],
    ['commission_paise_per_qtl', s('आडत', 'आढ़त', 'Commission')],
    ['loading_paise_per_qtl', s('हमाली', 'हमाली', 'Loading')],
    ['storage_paise_per_qtl', s('साठवण', 'भंडारण', 'Storage')],
    ['spoilage_paise_per_qtl', s('घट', 'नुकसान', 'Spoilage')],
  ];
  const spoken = o && v && verdict
    ? `${title}. ${s('आजचा भाव', 'आज का भाव', 'Today’s rate')} ${rs(o.latest.modal_paise_per_qtl)}. ${verdict.title}. ${s('अपेक्षित नफा', 'अपेक्षित लाभ', 'Expected gain')} ${rs(v.expected_gain_paise)}. ${s('सर्वात वाईट स्थिती', 'सबसे बुरी स्थिति', 'Worst case')} ${rs(v.worst_case_paise)}.`
    : title;

  return (
    <div className="km km-page">
      <div className="km-wrap km-herowrap"><section className="km-hero">
        <img key={crop.id} className="km-hero-img" src={heroSrc(crop.name)} alt="" />
        <div className="km-wrap">
          <p className="km-hi">{first ? s(`रामराम, ${first}`, `नमस्ते, ${first}`, `Namaste, ${first}`) : null}</p>
          <h1 lang={locale}>{title}</h1>
          <div className="km-where"><PlacePickers /></div>
          {o ? (
            <>
              <div className="km-rate">
                <div>
                  <div className="km-price">{rs(o.latest.modal_paise_per_qtl)}<small>{s('प्रति क्विंटल', 'प्रति क्विंटल', 'per quintal')}</small></div>
                  {o.change_7d_paise_per_qtl != null ? (
                    <span className={`km-chg ${up ? 'up' : 'dn'}`} style={{ marginTop: 12 }}>
                      <Ic name={up ? 'trending-up' : 'trending-down'} />
                      {s(`७ दिवसांत ${rs(Math.abs(o.change_7d_paise_per_qtl))} ${up ? 'वाढ' : 'घट'}`, `7 दिन में ${rs(Math.abs(o.change_7d_paise_per_qtl))} ${up ? 'बढ़त' : 'गिरावट'}`, `${up ? 'Up' : 'Down'} ${rs(Math.abs(o.change_7d_paise_per_qtl))} in 7 days`)}
                    </span>
                  ) : null}
                </div>
                <div className="km-band">
                  <div className="km-band-rule"><i style={{ left: `${at}%` }} /></div>
                  <dl>
                    <div><dt>{s('३० दिवसांत किमान', '30 दिन में न्यूनतम', '30-day low')}</dt><dd>{rs(lo)}</dd></div>
                    <div style={{ textAlign: 'center' }}><dt>{s('सरासरी', 'औसत', 'Average')}</dt><dd>{rs(o.avg_30d_paise_per_qtl)}</dd></div>
                    <div style={{ textAlign: 'right' }}><dt>{s('कमाल', 'अधिकतम', 'High')}</dt><dd>{rs(hi)}</dd></div>
                  </dl>
                </div>
              </div>
              <p className="km-src">{sourceLine(o, say)}</p>
            </>
          ) : (
            <p className="km-src" style={{ fontSize: 17, marginTop: 28 }}>
              {loading ? s('भाव आणत आहे…', 'भाव ला रहे हैं…', 'Getting today’s rate…') : s('या बाजारात या पिकाचा अलीकडचा भाव नाही.', 'इस मंडी में इस फसल का हाल का भाव नहीं है।', 'No recent rate for this crop in this market.')}
            </p>
          )}
        </div>
      </section></div>
      <CropStrip />

      <section className="km-wrap km-sec">
        {loading ? <Skel h={420} /> : failed || !o || !v || !verdict ? (
          <Empty
            title={s('या पिकासाठी सल्ला देण्याइतकी माहिती नाही', 'इस फसल के लिए सलाह देने लायक जानकारी नहीं है', 'Not enough data to advise on this crop')}
            body={s('दुसरे पीक किंवा बाजार निवडा.', 'दूसरी फसल या मंडी चुनें।', 'Pick another crop or market above.')}
            action={<button className="km-btn ghost" onClick={() => refetch()}>{s('पुन्हा पहा', 'फिर देखें', 'Try again')}</button>}
          />
        ) : (
          <div className="km-advice even">
            <div className="km-sheet">
              <h2 className={`km-verdict ${verdict.tone}`}>{verdict.title}</h2>
              <p className="km-lede">{explain}</p>
              {v.action !== 'NO_ADVICE' ? (
                <dl className="km-pair">
                  <div><dt>{s('अपेक्षित नफा', 'अपेक्षित लाभ', 'Expected gain')}</dt><dd className={(v.expected_gain_paise ?? 0) >= 0 ? 'km-good' : 'km-bad'}>{rs(v.expected_gain_paise)}</dd></div>
                  <div><dt>{s('सर्वात वाईट स्थिती', 'सबसे बुरी स्थिति', 'Worst case')}</dt><dd className={(v.worst_case_paise ?? 0) < 0 ? 'km-bad' : ''}>{rs(v.worst_case_paise)}</dd></div>
                </dl>
              ) : null}
              <p className="km-note" style={{ marginTop: 12 }}>{s(`${n(v.quantity_kg / 100)} क्विंटलसाठी, सर्व खर्च वजा करून`, `${n(v.quantity_kg / 100)} क्विंटल के लिए, सारे खर्च घटाकर`, `For ${n(v.quantity_kg / 100)} quintals, after all costs`)}</p>
              <div className="km-row">
                <button className="km-btn" onClick={() => navigation.navigate('S9_Verdict')}>{s('सल्ला असा का?', 'सलाह ऐसी क्यों?', 'See why')}</button>
                <ListenButton text={spoken} />
              </div>
              {costs ? (
                <details>
                  <summary>{s('खर्चाचा हिशोब', 'खर्च का हिसाब', 'Costs included')}</summary>
                  <dl className="km-costs">
                    {COST.filter(([k]) => costs[k] != null).map(([k, label]) => <div key={k}><dt>{label}</dt><dd>{rs(costs[k])}</dd></div>)}
                    <div className="tot"><dt>{s('एकूण, प्रति क्विंटल', 'कुल, प्रति क्विंटल', 'Total per quintal')}</dt><dd>{rs(costs.total_paise_per_qtl)}</dd></div>
                  </dl>
                </details>
              ) : null}
            </div>

            <div className="km-sheet">
              <div className="km-charthead">
                <h3>{s('भाव कुठे चालला आहे', 'भाव किधर जा रहा है', 'Where the rate is heading')}</h3>
                <div className="km-seg" role="group" aria-label={s('मागील दिवस', 'पिछले दिन', 'Past days')}>
                  {([7, 14, 30] as const).map(d => <button key={d} aria-pressed={days === d} onClick={() => setDays(d)}>{n(d)} {s('दिवस', 'दिन', 'days')}</button>)}
                </div>
              </div>
              <PriceChart o={o} days={days} />
              {fc.length ? (
                <dl className="km-miles">
                  <div><dt>{s('आज', 'आज', 'Today')}</dt><dd>{rs(o.latest.modal_paise_per_qtl)}</dd></div>
                  <div><dt>{s('७ व्या दिवशी', '7वें दिन', 'Day 7')}</dt><dd>{rs(fc[Math.min(6, fc.length - 1)]!.p50_paise_per_qtl)}</dd></div>
                  <div><dt>{s('१४ व्या दिवशी', '14वें दिन', 'Day 14')}</dt><dd>{rs(fc[fc.length - 1]!.p50_paise_per_qtl)}</dd></div>
                </dl>
              ) : null}
              <details>
                <summary>{s('रोजचा तक्ता', 'रोज़ की तालिका', 'Daily figures')}</summary>
                <div style={{ overflowX: 'auto' }}>
                  <table>
                    <thead><tr><th>{s('तारीख', 'तारीख', 'Date')}</th><th>{s('किमान', 'न्यूनतम', 'Low')}</th><th>{s('सरासरी', 'औसत', 'Modal')}</th><th>{s('कमाल', 'अधिकतम', 'High')}</th></tr></thead>
                    <tbody>{o.history.slice(-days).reverse().map(p => <tr key={p.obs_date}><td>{day(p.obs_date)}</td><td>{rs(p.min_paise_per_qtl)}</td><td><b>{rs(p.modal_paise_per_qtl)}</b></td><td>{rs(p.max_paise_per_qtl)}</td></tr>)}</tbody>
                  </table>
                </div>
              </details>
            </div>
          </div>
        )}
      </section>

      {o && o.nearby.rows.length ? (
        <section className="km-wrap" style={{ paddingBottom: 'clamp(40px,5.5vw,76px)' }}>
          <div className="km-head">
            <div>
              <h2 className="km-h2">{s('कुठे विकल्यास हातात जास्त येईल', 'कहाँ बेचने पर हाथ में ज़्यादा आएगा', 'Where you take home the most')}</h2>
              <p className="km-lede">{s('वाहतूक, आडत आणि हमाली वजा करून.', 'ढुलाई, आढ़त और हमाली घटाकर।', 'After transport, commission and loading.')}</p>
            </div>
            <button className="km-link" onClick={() => navigation.navigate('Prices')}>{s('सर्व बाजार पहा', 'सभी मंडियाँ देखें', 'See all markets')}</button>
          </div>
          <MandiTable rows={o.nearby.rows.slice(0, 5)} />
        </section>
      ) : null}

      <section style={{ background: 'var(--sunk2)' }}>
        <div className="km-wrap km-sec">
          <div className="km-head">
            <h2 className="km-h2">{s('माझा शेतमाल', 'मेरी उपज', 'My produce')}</h2>
            <button className="km-link" onClick={() => navigation.navigate('MyLots')}>{s('सर्व लॉट पहा', 'सभी लॉट देखें', 'Manage all lots')}</button>
          </div>
          {lots && lots.length ? (
            <div className="km-lots">{lots.slice(0, 4).map(l => <LotCard key={l.id} lot={l} onOpen={() => navigation.navigate('MyLots')} />)}</div>
          ) : (
            <Empty title={s('अजून एकही लॉट नाही', 'अभी कोई लॉट नहीं', 'No lots yet')} action={<button className="km-btn" onClick={() => navigation.navigate('MyLots')}>{s('शेतमाल नोंदवा', 'उपज जोड़ें', 'Add produce')}</button>} />
          )}
        </div>
      </section>
      <WebFooter />
    </div>
  );
}
