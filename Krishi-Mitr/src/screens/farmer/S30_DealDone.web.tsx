import React from 'react';
import { formatQuintal } from '../../lib/money';
import { Empty, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { TxDto } from '../../types/api';

export default function S30_DealDone({ route, navigation }: { route: any; navigation: any }) {
  const { t, rs, locale } = useSay();
  const tx = route.params?.tx as TxDto | undefined;
  const toDeals = () => navigation.getParent()?.navigate('Deals', { screen: 'S31_DealsList' });
  if (!tx) return <div className="km km-page"><div className="km-wrap km-sec"><Empty title={t('dl_title')} action={<button className="km-btn" onClick={toDeals}>{t('tab_deals')}</button>} /></div></div>;
  return (
    <Split inApp photo="sunrise" caption={t('dd_subtitle')} title={t('dd_title')} speak={t('dd_narr_agreed', { rate: rs(tx.price_paise_per_qtl), qty: formatQuintal(tx.qty_kg, locale) })}>
      <div className="km-form">
        <div><p className="km-mut">{t('dd_net_label')}</p><div className="km-price km-good">{rs(tx.net_paise)}</div></div>
        <dl className="km-costs" style={{ fontSize: 17, marginTop: 0 }}><div><dt>{t('dd_gross')}</dt><dd>{rs(tx.gross_paise)}</dd></div><div><dt>{t('dd_deductions')}</dt><dd>−{rs(tx.deductions_paise)}</dd></div><div className="tot"><dt>{t('dd_net_label')}</dt><dd>{rs(tx.net_paise)}</dd></div></dl>
        <p className="km-note">{t('dd_status_note')}</p>
        <div className="km-foot1" style={{ marginTop: 0 }}><button className="km-btn main" onClick={() => navigation.navigate('S32_DealTracking', { tx_id: tx.id })}>{t('dd_track_cta')}</button><button className="km-link" onClick={toDeals}>{t('tab_deals')}</button></div>
      </div>
    </Split>
  );
}
