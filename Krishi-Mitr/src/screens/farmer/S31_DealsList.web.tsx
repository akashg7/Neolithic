/** Deals — website version of S31. Stages come from the real transaction. */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ListenButton } from '../../components/ui/ListenButton';
import { WebFooter } from '../../components/web/WebFooter';
import { getLots, getOffers, getTransactions } from '../../lib/api';
import { Banner } from '../../web/Banner';
import { Empty, Skel, useSay } from '../../web/kit';
import { OfferRow } from '../../web/OfferRow';
import type { TxStatus } from '../../types/api';

const ORDER: TxStatus[] = ['ESCROW_HELD', 'DISPATCHED', 'DELIVERED', 'RELEASED'];
const KEYS = ['em_escrow', 'em_dispatched', 'em_delivered', 'em_released'];

export default function S31_DealsList({ navigation }: { navigation: any }) {
  const { s, n, t, rs } = useSay();
  const [f, setF] = useState<'agreed' | 'talking'>('agreed');
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['offers', 'talks'], queryFn: getOffers });
  const { data: txs } = useQuery({ queryKey: ['transactions'], queryFn: getTransactions });
  const { data: lots } = useQuery({ queryKey: ['lots'], queryFn: getLots });
  const rows = (data ?? []).filter(o => o.status === (f === 'agreed' ? 'ACCEPTED' : 'OPEN')).sort((a, b) => b.created_at.localeCompare(a.created_at));
  const spoken = rows.length ? t('dl_narr_count', { n: n(rows.length) }) + ' ' + rows.map(o => rs(o.price_paise_per_qtl)).join(', ') : t('dl_empty_agreed');

  return (
    <div className="km km-page">
      <Banner scene="truck" title={t('dl_title')} sub={t('dl_subtitle')}><ListenButton text={spoken} /></Banner>
      <section className="km-wrap km-sec" style={{ maxWidth: 1060 }}>
        <div className="km-seg" role="group" style={{ marginBottom: 24 }}>
          <button aria-pressed={f === 'agreed'} onClick={() => setF('agreed')}>{t('dl_filter_agreed')}</button>
          <button aria-pressed={f === 'talking'} onClick={() => setF('talking')}>{t('dl_filter_talking')}</button>
        </div>
        {isLoading ? <Skel h={220} /> : error && !data ? <Empty title={t('offers_fetch_error')} action={<button className="km-btn ghost" onClick={() => refetch()}>{t('chat_retry')}</button>} />
          : !rows.length ? <Empty title={t(f === 'agreed' ? 'dl_empty_agreed' : 'dl_empty_talking')} body={t(f === 'agreed' ? 'dl_empty_agreed_body' : 'dl_empty_talking_body')} />
          : rows.map(o => {
            const tx = txs?.find(x => x.offer_id === o.id);
            const at = tx ? ORDER.indexOf(tx.status) : -1;
            return (
              <OfferRow key={o.id} offer={o} lots={lots} state={t(f === 'agreed' ? 'dl_status_agreed' : 'chat_status_open')}>
                {f === 'agreed' ? tx ? (
                  <>
                    {['DISPUTED', 'REFUNDED', 'CANCELLED'].includes(tx.status)
                      ? <p className="km-quote">{t(`em_off_${tx.status.toLowerCase()}`)}</p>
                      : <ul className="km-steps">{KEYS.map((k, i) => <li key={k} className={i <= at ? 'on' : ''}>{t(k)}</li>)}</ul>}
                    <div className="km-row"><button className="km-link" onClick={() => navigation.navigate('S32_DealTracking', { tx_id: tx.id })}>{t('dl_track_cta')}</button></div>
                  </>
                ) : <p className="km-quote">{t('dl_no_tracking_note')}</p>
                  : <div className="km-row"><button className="km-btn" onClick={() => navigation.getParent()?.navigate('Talks', { screen: 'S27_Bargaining', params: { offer_id: o.id } })}>{t('bfl_open_talk')}</button></div>}
              </OfferRow>
            );
          })}
        {f === 'agreed' && rows.length ? <p className="km-note" style={{ marginTop: 20 }}>{s('पैसे आधी एस्क्रोमध्ये राहतात. माल पोहोचल्यावर तुम्हाला मिळतात.', 'पैसे पहले एस्क्रो में रहते हैं। माल पहुँचने पर आपको मिलते हैं।', 'The money is held in escrow first and released to you after delivery.')}</p> : null}
      </section>
      <WebFooter />
    </div>
  );
}
