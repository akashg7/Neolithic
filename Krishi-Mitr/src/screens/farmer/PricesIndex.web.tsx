/** Market — website version: compare mandis, arrivals, rate spread, model card. */
import React from 'react';
import { WebFooter } from '../../components/web/WebFooter';
import { ListenButton } from '../../components/ui/ListenButton';
import { Banner } from '../../web/Banner';
import { CropStrip, cropName, Empty, PlacePickers, Skel, sourceLine, useMarket, useSay } from '../../web/kit';
import { MandiTable } from '../../web/MandiTable';
import { PriceChart } from '../../web/PriceChart';

export default function PricesIndex({ navigation }: { navigation: any }) {
  const say = useSay();
  const { s, rs, n, locale } = say;
  const { crop, o, loading, refetch, activeFilter, setActiveFilter } = useMarket();
  const title = cropName(crop, locale);
  let rows = o ? [...o.nearby.rows] : [];
  if (activeFilter === 'nearby') rows = rows.filter(r => r.distance_km <= 50);
  if (activeFilter === 'highest') rows.sort((a, b) => b.gross_paise_per_qtl - a.gross_paise_per_qtl);
  const up = (o?.change_7d_bps ?? 0) >= 0;
  const best = o ? [...o.nearby.rows].sort((a, b) => b.net_paise_per_qtl - a.net_paise_per_qtl)[0] : undefined;
  const spoken = best ? s(`${title}. हातात सर्वात जास्त ${best.name_mr}: ${rs(best.net_paise_per_qtl)}.`, `${title}. हाथ में सबसे ज़्यादा ${best.name_mr}: ${rs(best.net_paise_per_qtl)}.`, `${title}. Highest take-home is ${best.name ?? best.name_mr}: ${rs(best.net_paise_per_qtl)}.`) : title;

  return (
    <div className="km km-page">
      <Banner scene="mandi" title={s('बाजारभाव', 'मंडी भाव', 'Market rates')} sub={s('जवळच्या बाजारांचे भाव आणि हातात येणारी रक्कम एकाच ठिकाणी.', 'पास की मंडियों के भाव और हाथ में आने वाली रकम एक जगह।', 'Rates at nearby markets, and what you take home from each.')}>
        <PlacePickers />
      </Banner>
      <CropStrip />
      <section className="km-wrap" style={{ paddingBlock: '20px 64px' }}>
        {loading ? <Skel h={380} /> : !o ? (
          <Empty title={s('या पिकाचा अलीकडचा भाव नाही', 'इस फसल का हाल का भाव नहीं', 'No recent rate for this crop')} body={s('दुसरे पीक किंवा बाजार निवडा.', 'दूसरी फसल या मंडी चुनें।', 'Pick another crop or market.')} action={<button className="km-btn ghost" onClick={() => refetch()}>{s('पुन्हा पहा', 'फिर देखें', 'Try again')}</button>} />
        ) : (
          <>
            <div className="km-head">
              <div>
                <h2 className="km-h2">{s(`${title}: कोणत्या बाजारात किती`, `${title}: किस मंडी में कितना`, `${title}, market by market`)}</h2>
                <p className="km-lede">{sourceLine(o, say)}</p>
              </div>
              <div className="km-row" style={{ marginTop: 0 }}>
                <div className="km-seg" role="group">
                  {(['all', 'nearby', 'highest'] as const).map(f => (
                    <button key={f} aria-pressed={activeFilter === f} onClick={() => setActiveFilter(f)}>
                      {f === 'all' ? s('सर्व', 'सभी', 'All') : f === 'nearby' ? s('५० किमीत', '50 किमी में', 'Within 50 km') : s('जास्त भाव', 'ऊँचा भाव', 'Highest rate')}
                    </button>
                  ))}
                </div>
                <ListenButton text={spoken} />
              </div>
            </div>
            {rows.length ? <MandiTable rows={rows} /> : <Empty title={s('५० किमीत दुसरा बाजार नाही', '50 किमी में दूसरी मंडी नहीं', 'No other market within 50 km')} />}

            <div className="km-advice" style={{ marginTop: 64, gridTemplateColumns: 'minmax(0,7fr) minmax(0,4fr)' }} data-stack>
              <div className="km-sheet"><div className="km-charthead"><h3>{s('३० दिवस आणि पुढचे १४', '30 दिन और अगले 14', 'Last 30 days, next 14')}</h3></div><PriceChart o={o} days={30} /></div>
              <div>
                <h2 className="km-h2">{s('आजचा बाजार', 'आज की मंडी', 'Today at the market')}</h2>
                <dl className="km-costs" style={{ fontSize: 17 }}>
                  <div><dt>{s('आवक', 'आवक', 'Arrivals')}</dt><dd>{n(o.latest.arrivals_qtl)} {s('क्विं.', 'क्विं.', 'qtl')}</dd></div>
                  <div><dt>{s('किमान भाव', 'न्यूनतम भाव', 'Lowest rate')}</dt><dd>{rs(o.latest.min_paise_per_qtl)}</dd></div>
                  <div><dt>{s('सरासरी भाव', 'औसत भाव', 'Modal rate')}</dt><dd>{rs(o.latest.modal_paise_per_qtl)}</dd></div>
                  <div><dt>{s('कमाल भाव', 'अधिकतम भाव', 'Highest rate')}</dt><dd>{rs(o.latest.max_paise_per_qtl)}</dd></div>
                  {o.change_7d_paise_per_qtl != null ? <div><dt>{s('७ दिवसांत', '7 दिन में', 'Over 7 days')}</dt><dd className={up ? 'km-good' : 'km-bad'}>{up ? '+' : ''}{rs(o.change_7d_paise_per_qtl)}</dd></div> : null}
                </dl>
                <div className="km-row"><button className="km-btn ghost" onClick={() => navigation.navigate('S8_ModelCard')}>{s('अंदाज किती बरोबर येतो?', 'अनुमान कितना सही होता है?', 'How accurate is the forecast?')}</button></div>
              </div>
            </div>
          </>
        )}
      </section>
      <WebFooter />
    </div>
  );
}
