import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTransaction } from '../../lib/api';
import { formatQuintal } from '../../lib/money';
import { Empty, Skel, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S33_Settled({ route, navigation }: { route: any; navigation: any }) {
  const { t, rs, locale } = useSay();
  const id: string | undefined = route.params?.tx_id;
  const { data: tx, isLoading } = useQuery({ queryKey: ['tx', id], queryFn: () => getTransaction(id!), enabled: !!id });
  const back = () => (navigation.canGoBack() ? navigation.goBack() : navigation.getParent()?.navigate('Deals'));
  return (
    <Split inApp photo="sunrise" caption={t('st_paid_badge')} title={t('st_title')} onBack={back}>
      <div className="km-form">{isLoading ? <Skel h={260} /> : !tx ? <Empty title={t('st_no_tx_title')} body={t('tr_no_tx_body')} /> : tx.status !== 'RELEASED' ? <Empty title={t('st_not_released')} action={<button className="km-btn" onClick={back}>{t('back_button')}</button>} /> : (
        <><div className="km-price km-good">{rs(tx.net_paise)}</div><dl className="km-costs" style={{ fontSize: 17 }}>{tx.qty_kg ? <><div><dt>{t('st_rate')}</dt><dd>{rs(tx.price_paise_per_qtl)}</dd></div><div><dt>{t('st_qty')}</dt><dd>{formatQuintal(tx.qty_kg, locale)}</dd></div></> : null}<div><dt>{t('dd_gross')}</dt><dd>{rs(tx.gross_paise)}</dd></div><div><dt>{t('dd_deductions')}</dt><dd>−{rs(tx.deductions_paise)}</dd></div><div className="tot"><dt>{t('dd_net_label')}</dt><dd>{rs(tx.net_paise)}</dd></div></dl><p className="km-note">{t('st_receipt_note')}</p></>
      )}</div>
    </Split>
  );
}
