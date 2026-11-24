import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEscrowEvents, getTransaction } from '../../lib/api';
import { formatQuintal } from '../../lib/money';
import { Empty, Skel, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { TxStatus } from '../../types/api';

const ORDER: TxStatus[] = ['ESCROW_HELD', 'DISPATCHED', 'DELIVERED', 'RELEASED'];
const KEYS = ['em_escrow', 'em_dispatched', 'em_delivered', 'em_released'];

export default function S32_DealTracking({ route, navigation }: { route: any; navigation: any }) {
  const { t, s, rs, day, locale } = useSay();
  const id: string | undefined = route.params?.tx_id;
  const q = useQuery({ queryKey: ['tx', id], queryFn: () => getTransaction(id!), enabled: !!id });
  const ev = useQuery({ queryKey: ['tx', id, 'events'], queryFn: () => getEscrowEvents(id!), enabled: !!id });
  const tx = q.data;
  const at = tx ? ORDER.indexOf(tx.status) : -1;
  const photo = at >= 3 ? 'sunrise' : at === 2 ? 'gate' : at === 1 ? 'truck' : 'scale';
  const back = () => (navigation.canGoBack() ? navigation.goBack() : navigation.getParent()?.navigate('Deals'));
  return (
    <Split inApp photo={photo} caption={tx ? t(`tr_status_${tx.status.toLowerCase()}`) : t('tr_title')} title={t('tr_title')} onBack={back} speak={tx ? t(`tr_status_${tx.status.toLowerCase()}`) : t('tr_title')}>
      <div className="km-form">
        {q.isLoading ? <Skel h={300} /> : !tx ? <Empty title={t('tr_no_tx_title')} body={t('tr_no_tx_body')} action={<button className="km-btn" onClick={back}>{t('tab_deals')}</button>} /> : (
          <>
            <div><p className="km-mut">{t('dd_net_label')}</p><div className="km-price">{rs(tx.net_paise)}</div>{tx.qty_kg ? <p className="km-mut" style={{ marginTop: 8 }}>{t('dd_rate_and_qty', { rate: rs(tx.price_paise_per_qtl), qty: formatQuintal(tx.qty_kg, locale) })}</p> : null}</div>
            {['DISPUTED', 'REFUNDED', 'CANCELLED'].includes(tx.status) ? <p className="km-err">{t(`em_off_${tx.status.toLowerCase()}`)}</p> : <ul className="km-steps">{KEYS.map((k, i) => <li key={k} className={i <= at ? 'on' : ''}>{t(k)}</li>)}</ul>}
            <div><b>{t('tr_timeline_title')}</b>{ev.data?.length ? <ul className="km-track">{ev.data.map(e => <li key={e.id}><b>{t(`tr_status_${e.to_status.toLowerCase()}`)}</b><p className="km-note">{day(e.created_at, { day: 'numeric', month: 'long' })}{e.note ? `. ${e.note}` : ''}</p></li>)}</ul> : <p className="km-mut">{t('tr_timeline_empty')}</p>}</div>
            {tx.status === 'RELEASED' ? <button className="km-btn" onClick={() => navigation.navigate('S33_Settled', { tx_id: tx.id })}>{t('tr_settled_cta')}</button> : <p className="km-note">{s('प्रत्येक टप्पा नोंदवला जातो आणि बदलता येत नाही.', 'हर चरण दर्ज होता है और बदला नहीं जा सकता।', 'Every stage is recorded and can’t be edited.')}</p>}
          </>
        )}
      </div>
    </Split>
  );
}
