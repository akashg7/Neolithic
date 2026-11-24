/** Set the asking price and publish. Prices come from this lot's crop and market, and publishing calls the API (it never did). */
import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getLot, getMarketOverview, publishLot } from '../../lib/api';
import { formatQuintal, quintalValuePaise } from '../../lib/money';
import { cropLabel, Empty, heroSrc, marketLabel, Skel, useRefNames, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S22_PricePublish({ route, navigation }: { route: any; navigation: any }) {
  useRefNames();
  const { t, s, rs, locale } = useSay();
  const qc = useQueryClient();
  const id: string | undefined = route.params?.lot_id;
  const lotQ = useQuery({ queryKey: ['lots', id], queryFn: () => getLot(id!), enabled: !!id });
  const lot = lotQ.data;
  const oq = useQuery({ queryKey: ['overview', lot?.commodity_id, lot?.market_id], queryFn: () => getMarketOverview(lot!.commodity_id, lot!.market_id), enabled: !!lot });
  const o = oq.data;
  const [price, setPrice] = useState<number | null>(null);
  const modal = o?.latest.modal_paise_per_qtl ?? 0;
  const ask = price ?? Math.round(modal / 1000) * 1000;
  const lo = Math.floor((modal * 0.6) / 1000) * 1000, hi = Math.ceil((modal * 1.4) / 1000) * 1000;
  const cost = o?.verdict.itemised_costs;
  // Selling now: no storage or spoilage.
  const perQtl = cost ? (cost.transport_paise_per_qtl ?? 0) + (cost.commission_paise_per_qtl ?? 0) + (cost.loading_paise_per_qtl ?? 0) : null;
  const gross = lot ? quintalValuePaise(ask, lot.qty_kg) : 0;
  const ded = lot && perQtl != null ? quintalValuePaise(perQtl, lot.qty_kg) : null;
  const pub = useMutation({
    mutationFn: () => publishLot(id!, ask),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['lots'] }); navigation.navigate('S23_PublishedRadar', { lot_id: id, asking_paise: ask }); },
  });
  const set = (v: number) => setPrice(Math.max(lo, Math.min(hi, v)));
  return (
    <Split inApp photo={lot ? heroSrc(lot.commodity_id) : 'mandi'} caption={lot ? cropLabel(lot.commodity_id, locale) : t('pp_title')} sub={lot ? `${formatQuintal(lot.qty_kg, locale)} ${s('क्विंटल', 'क्विंटल', 'quintals')}, ${marketLabel(lot.market_id, locale)}` : undefined} title={t('pp_title')} step={5} of={5}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S15_MyLots'))} speak={o ? t('pp_narr_ask', { rate: rs(ask), qty: formatQuintal(lot!.qty_kg, locale), gross: rs(gross) }) : t('pp_title')}>
      <div className="km-form">
        {lotQ.isLoading || oq.isLoading ? <Skel h={360} /> : !lot || !o ? <Empty title={s('या लॉटसाठी बाजारभाव मिळाला नाही', 'इस लॉट का मंडी भाव नहीं मिला', 'No market rate found for this lot')} action={<button className="km-btn ghost" onClick={() => { void lotQ.refetch(); void oq.refetch(); }}>{t('chat_retry')}</button>} /> : (
          <>
            <div className="km-field"><b>{t('pp_asking_label')}</b>
              <div className="km-step"><button aria-label="−" onClick={() => set(ask - 1000)}>−</button><output>{rs(ask)}</output><button aria-label="+" onClick={() => set(ask + 1000)}>+</button></div>
              <input className="km-range" type="range" aria-label={t('pp_asking_label')} min={lo} max={hi} step={1000} value={ask} onChange={e => set(Number(e.target.value))} />
              <p className={ask > o.latest.max_paise_per_qtl ? 'km-bad' : 'km-mut'}>{t('pp_bench_modal')} <b>{rs(modal)}</b>. {ask > o.latest.max_paise_per_qtl ? t('pp_above_range') : ask < o.latest.min_paise_per_qtl ? t('pp_below_range') : t('pp_in_range')}.</p>
            </div>
            <dl className="km-costs" style={{ fontSize: 17, marginTop: 0 }}>
              <div><dt>{formatQuintal(lot.qty_kg, locale)} × {rs(ask)}</dt><dd>{rs(gross)}</dd></div>
              {ded != null ? <div><dt>{t('pp_deductions_row', { perQtl: rs(perQtl) })}</dt><dd>−{rs(ded)}</dd></div> : null}
              <div className="tot"><dt>{t('pp_net_label')}</dt><dd style={{ fontSize: 28 }} className="km-good">{rs(gross - (ded ?? 0))}</dd></div>
            </dl>
            <p className="km-note">{t('pp_escrow_note')}</p>
            {pub.isError ? <p className="km-err" role="alert">{(pub.error as Error)?.message || t('network_error_generic')}</p> : null}
            <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={pub.isPending} onClick={() => pub.mutate()}>{t('pp_publish_cta')}</button>
            <p className="km-note">{t('pp_draft_note')}</p>
          </>
        )}
      </div>
    </Split>
  );
}
