/** One negotiation. Compared with the rate for this lot's own crop and market. */
import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ListenButton } from '../../components/ui/ListenButton';
import { acceptOffer, counterOffer, getLots, getMarketOverview, getOfferThread, rejectOffer } from '../../lib/api';
import { noteText } from '../../lib/offerNote';
import { formatQuintal, quintalValuePaise } from '../../lib/money';
import { cropLabel, Empty, heroSrc, marketLabel, Skel, useRefNames, useSay } from '../../web/kit';

const MAX = 3;

export default function S27_Bargaining({ route, navigation }: { route: any; navigation: any }) {
  useRefNames();
  const { t, s, n, rs, day, locale } = useSay();
  const qc = useQueryClient();
  const id: string | undefined = route.params?.offer_id;
  const th = useQuery({ queryKey: ['offers', id, 'thread'], queryFn: () => getOfferThread(id!), enabled: !!id });
  const { data: lots, isLoading: lotsLoading } = useQuery({ queryKey: ['lots'], queryFn: getLots });
  const thread = th.data ?? [];
  const latest = thread[thread.length - 1];
  const lot = lots?.find(l => latest?.lots.some(x => String(x.lot_id) === l.id));
  const { data: o } = useQuery({ queryKey: ['overview', lot?.commodity_id, lot?.market_id], queryFn: () => getMarketOverview(lot!.commodity_id, lot!.market_id), enabled: !!lot });
  const [mode, setMode] = useState<null | 'counter' | 'accept' | 'reject'>(null);
  const [ask, setAsk] = useState<number | null>(null);
  const modal = o?.latest.modal_paise_per_qtl ?? null;
  const floor = latest?.price_paise_per_qtl ?? 0;
  const price = ask ?? Math.max(floor, modal ?? floor);
  const mine = latest?.initiator === 'BUYER' && latest.status === 'OPEN';
  const last = (latest?.round ?? 0) >= MAX;
  const total = latest ? quintalValuePaise(latest.price_paise_per_qtl, latest.qty_kg) : 0;
  const act = useMutation({
    mutationFn: async (k: 'accept' | 'reject' | 'counter') => (k === 'accept' ? acceptOffer(latest!.id) : k === 'reject' ? (await rejectOffer(latest!.id), null) : (await counterOffer(latest!.id, { price_paise_per_qtl: price }), null)),
    onSuccess: tx => {
      for (const key of ['offers', 'lots', 'transactions']) void qc.invalidateQueries({ queryKey: [key] });
      setMode(null);
      if (tx) navigation.navigate('S30_DealDone', { tx }); else navigation.navigate('S37_Talks', undefined, { pop: true }); // a counter is a new offer, listed in Talks
    },
  });
  const back = () => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S37_Talks'));
  const diff = modal != null && latest ? latest.price_paise_per_qtl - modal : null;
  if (th.isLoading || lotsLoading) return <div className="km km-page"><div className="km-wrap km-sec"><Skel h={420} /></div></div>;
  if (!latest) return <div className="km km-page"><div className="km-wrap km-sec"><Empty title={t('bg_empty_title')} body={t('bg_empty_body')} action={<button className="km-btn" onClick={back}>{t('back_button')}</button>} /></div></div>;
  return (
    <div className="km km-page">
      <div className="km-wrap km-herowrap"><section className="km-banner"><img src={lot ? heroSrc(lot.commodity_id) : '/images/scene/tea.jpg'} alt="" /><div className="km-wrap">
        <button className="km-link" style={{ color: '#fff', marginBottom: 'auto', alignSelf: 'flex-start' }} onClick={back}>{t('back_button')}</button>
        <h1>{lot ? cropLabel(lot.commodity_id, locale) : t('bg_title')}</h1>
        <p>{formatQuintal(latest.qty_kg, locale)} {s('क्विंटल', 'क्विंटल', 'quintals')}{lot ? `, ${t(`lot_grade_${lot.grade.toLowerCase()}`)}, ${marketLabel(lot.market_id, locale)}` : ''}</p>
      </div></section></div>
      <section className="km-wrap km-sec" style={{ paddingTop: 32 }}><div className="km-two">
        <div><div className="km-head" style={{ marginBottom: 18 }}><h2 className="km-h2" style={{ fontSize: 24 }}>{t('bg_audit_title')}</h2><ListenButton text={t('bg_narr_offer', { rate: rs(latest.price_paise_per_qtl), total: rs(total), qty: formatQuintal(latest.qty_kg, locale) })} /></div>
          <div style={{ display: 'grid', gap: 14 }}>{thread.map(r => { const note = noteText(r.note, t); return (
            <div key={r.id} className={`km-round${r.initiator === 'FARMER' ? ' me' : ''}`}><div><b>{r.initiator === 'FARMER' ? t('chat_from_you') : t('chat_from_buyer')}</b><p className="km-note">{t('bg_round_n', { round: n(r.round) })}, {day(r.created_at)}</p></div><div style={{ textAlign: 'right' }}><strong>{rs(r.price_paise_per_qtl)}</strong><p className="km-note">{rs(quintalValuePaise(r.price_paise_per_qtl, r.qty_kg))}</p></div>{note ? <p className="km-quote" style={{ gridColumn: '1/-1' }}>{note}</p> : null}</div>); })}</div>
        </div>
        <aside className="km-sheet km-stick">
          <h3 className="km-h2" style={{ fontSize: 22 }}>{t('bg_matrix_title')}</h3>
          <dl className="km-pair"><div><dt>{t('bg_matrix_payout')}</dt><dd>{rs(total)}</dd></div>{diff != null ? <div><dt>{t('bg_matrix_vs_mandi')}</dt><dd className={diff >= 0 ? 'km-good' : 'km-bad'}>{diff >= 0 ? '+' : ''}{rs(diff)}</dd></div> : null}</dl>
          {modal != null ? <p className="km-note" style={{ marginTop: 10 }}>{t('bg_matrix_vs_mandi_note', { mandi: rs(modal) })}</p> : null}
          {!mine ? <p className="km-hint" style={{ marginTop: 20 }}>{latest.status === 'OPEN' ? t('chat_awaiting_them') : t(`chat_status_${latest.status.toLowerCase()}`)}</p> : mode === 'counter' ? (
            <div className="km-form" style={{ marginTop: 20, gap: 14 }}><b>{t('co_new_ask_label')}</b><div className="km-step"><button aria-label="−" onClick={() => setAsk(Math.max(floor, price - 1000))}>−</button><output style={{ fontSize: 34 }}>{rs(price)}<small>{rs(quintalValuePaise(price, latest.qty_kg))}</small></output><button aria-label="+" onClick={() => setAsk(price + 1000)}>+</button></div><p className="km-note">{t('co_rounds_left', { n: n(MAX - latest.round) })}</p>
              <button className="km-btn" disabled={act.isPending || price <= floor} onClick={() => act.mutate('counter')}>{t('co_send_cta', { rate: rs(price) })}</button><button className="km-link" onClick={() => setMode(null)}>{s('परत', 'वापस', 'Back')}</button></div>
          ) : mode ? (
            <div className="km-form" style={{ marginTop: 20, gap: 14 }}><b>{mode === 'accept' ? s(`${rs(total)} ला विकायचे नक्की?`, `${rs(total)} में बेचना पक्का?`, `Sell for ${rs(total)}?`) : s('ही बोली नाकारायची?', 'यह बोली ठुकराएँ?', 'Decline this offer?')}</b><p className="km-note">{mode === 'accept' ? t('bg_matrix_escrow_note') : s('हे परत बदलता येणार नाही.', 'यह वापस नहीं बदल सकते।', 'You can’t undo this.')}</p>
              <button className="km-btn" disabled={act.isPending} onClick={() => act.mutate(mode)}>{mode === 'accept' ? s('हो, विका', 'हाँ, बेचें', 'Yes, sell') : s('हो, नाकारा', 'हाँ, ठुकराएँ', 'Yes, decline')}</button><button className="km-link" onClick={() => setMode(null)}>{s('परत', 'वापस', 'Back')}</button></div>
          ) : (
            <div className="km-form" style={{ marginTop: 20, gap: 12 }}><button className="km-btn" style={{ minHeight: 60 }} onClick={() => setMode('accept')}>{t('bg_accept_cta', { rate: rs(latest.price_paise_per_qtl), total: rs(total) })}</button><button className="km-btn ghost" disabled={last} onClick={() => setMode('counter')}>{last ? t('bg_counter_spent') : t('bg_counter_cta')}</button><button className="km-link" style={{ justifySelf: 'center', color: 'var(--bad)' }} onClick={() => setMode('reject')}>{t('bg_decline_cta')}</button></div>
          )}
          {act.isError ? <p className="km-err" role="alert" style={{ marginTop: 14 }}>{(act.error as Error)?.message || t('network_error_generic')}</p> : null}
        </aside>
      </div></section>
    </div>
  );
}
