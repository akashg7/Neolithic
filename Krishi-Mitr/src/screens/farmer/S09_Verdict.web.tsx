/** The decision, explained. Uses the picked crop, market and quantity (was always onion, Lasalgaon, 40 qtl). */
import React from 'react';
import { ListenButton } from '../../components/ui/ListenButton';
import { WebFooter } from '../../components/web/WebFooter';
import { cropName, Empty, heroSrc, Ic, Skel, useSay, verdictOf } from '../../web/kit';
import { PriceChart } from '../../web/PriceChart';
import { setVerdictQty, useVerdict, type VerdictRouteParams } from '../../web/useVerdict';

export default function S09_Verdict({ route, navigation }: { route?: { params?: VerdictRouteParams }; navigation: any }) {
  const say = useSay();
  const { t, s, n, rs, locale } = say;
  const { crop, o, v, kg, vLoading, vRefetch } = useVerdict(route?.params);
  const back = () => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S4_Home'));
  const d = v ? verdictOf(v.action, v.hold_days, say) : null;
  const place = o ? (locale === 'en' ? o.market.name.replace(' APMC', '') : o.market.name_mr) : '';
  const COST: [keyof NonNullable<typeof v>['costs'], string, string][] = [
    ['transport_paise_per_qtl', s('वाहतूक', 'ढुलाई', 'Transport'), t('cb_desc_transport')], ['commission_paise_per_qtl', s('आडत', 'आढ़त', 'Commission'), t('cb_desc_commission')],
    ['loading_paise_per_qtl', s('हमाली', 'हमाली', 'Loading'), t('cb_desc_loading')], ['storage_paise_per_qtl', s('साठवण', 'भंडारण', 'Storage'), t('cb_desc_storage')], ['spoilage_paise_per_qtl', s('घट', 'नुकसान', 'Spoilage'), t('cb_desc_spoilage')],
  ];
  return (
    <div className="km km-page">
      <div className="km-wrap km-herowrap"><section className="km-banner">
        <img src={heroSrc(crop.name)} alt="" />
        <div className="km-wrap" style={{ minHeight: 330 }}>
          <button className="km-link" style={{ color: '#fff', marginBottom: 'auto', alignSelf: 'flex-start' }} onClick={back}>{t('back_button')}</button>
          <p style={{ fontSize: 18 }}>{cropName(crop, locale)}{place ? `, ${place}` : ''}</p>
          <h1 lang={locale}>{d ? d.title : s('सल्ला', 'सलाह', 'Advice')}</h1>
        </div>
      </section></div>
      <section className="km-wrap km-sec" style={{ paddingTop: 32 }}>
        {vLoading ? <Skel h={420} /> : !v || !o || !d ? <Empty title={t('verdict_empty')} body={s('दुसरे पीक किंवा बाजार निवडा.', 'दूसरी फसल या मंडी चुनें।', 'Pick another crop or market.')} action={<button className="km-btn ghost" onClick={vRefetch}>{t('chat_retry')}</button>} /> : (
          <div className="km-two">
            <div style={{ display: 'grid', gap: 28 }}>
              <div className="km-sheet">
                <div className="km-charthead"><h3>{s('किती माल आहे?', 'कितना माल है?', 'How much do you have?')}</h3><ListenButton text={`${d.title}. ${t('loan_compare_gain')} ${rs(v.expected_gain_paise)}. ${s('सर्वात वाईट स्थिती', 'सबसे बुरी स्थिति', 'Worst case')} ${rs(v.worst_case_paise)}.`} /></div>
                <div className="km-step" style={{ marginTop: 16 }}>
                  <button aria-label={s('एक क्विंटल कमी', 'एक क्विंटल कम', 'One quintal less')} onClick={() => setVerdictQty(kg - 100)}>−</button>
                  <output>{n(kg / 100)}<small>{s('क्विंटल', 'क्विंटल', 'quintals')}</small></output>
                  <button aria-label={s('एक क्विंटल जास्त', 'एक क्विंटल ज़्यादा', 'One quintal more')} onClick={() => setVerdictQty(kg + 100)}>+</button>
                </div>
                {v.action === 'NO_ADVICE' ? <p className="km-lede" style={{ marginTop: 20 }}>{locale === 'en' ? v.explain_en : v.explain_mr}</p> : (
                  <dl className="km-pair">
                    <div><dt>{s('अपेक्षित नफा', 'अपेक्षित लाभ', 'Expected gain')}</dt><dd className={(v.expected_gain_paise ?? 0) >= 0 ? 'km-good' : 'km-bad'}>{rs(v.expected_gain_paise)}</dd></div>
                    <div><dt>{s('सर्वात वाईट स्थिती', 'सबसे बुरी स्थिति', 'Worst case')}</dt><dd className={(v.worst_case_paise ?? 0) < 0 ? 'km-bad' : ''}>{rs(v.worst_case_paise)}</dd></div>
                  </dl>
                )}
              </div>
              <div className="km-sheet"><div className="km-charthead"><h3>{s('भाव कुठे चालला आहे', 'भाव किधर जा रहा है', 'Where the rate is heading')}</h3></div><PriceChart o={o} days={14} />
                <p className="km-note" style={{ marginTop: 14 }}>{t('vd_accuracy_note', { mase: v.model_card?.mase?.toFixed(2) ?? '–', coverage: v.model_card ? n(Math.round(v.model_card.coverage_80_bps / 100)) : '–' })}</p></div>
            </div>
            <div style={{ display: 'grid', gap: 28 }} className="km-stick">
              <div className="km-sheet">
                <h3 className="km-h2" style={{ fontSize: 22 }}>{s('खर्च, प्रति क्विंटल', 'खर्च, प्रति क्विंटल', 'Costs per quintal')}</h3>
                <dl className="km-costs">{COST.map(([k, l, desc]) => <div key={k}><dt>{l}<br /><small className="km-note">{desc}</small></dt><dd>{rs(v.costs?.[k])}</dd></div>)}
                  <div className="tot"><dt>{s('एकूण', 'कुल', 'Total')}</dt><dd>{rs(v.costs?.total_paise_per_qtl)}</dd></div></dl>
              </div>
              {v.pledge_quote ? <div className="km-sheet"><h3 className="km-h2" style={{ fontSize: 22 }}>{t('pledge_title')}</h3><p className="km-price" style={{ fontSize: 36, marginTop: 10 }}>{rs(v.pledge_quote.loan_paise)}</p><p className="km-mut">{t('loan_hero_sub')}</p><div className="km-row" style={{ marginTop: 14 }}><button className="km-link" onClick={() => navigation.navigate('S13_CropLoan')}>{t('loan_see_details')}</button></div></div> : null}
              <div><button className="km-btn" style={{ width: '100%', minHeight: 60 }} onClick={() => navigation.getParent()?.navigate('MyLots', { screen: 'S17_CameraGuide' })}><Ic name="tag" />{t('vd_list_lot_cta')}</button><p className="km-note" style={{ marginTop: 12 }}>{t('vd_no_hold_persist')}</p></div>
            </div>
          </div>
        )}
      </section>
      <WebFooter />
    </div>
  );
}
