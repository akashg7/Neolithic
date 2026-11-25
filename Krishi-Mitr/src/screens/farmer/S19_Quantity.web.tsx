/** What and how much. Saves the crop and market chosen here (it used to save onion at Lasalgaon for everyone). */
import React, { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createLot } from '../../lib/api';
import { cropName, heroSrc, PlacePickers, tileSrc, useKnownCrops, useMarket, useSay } from '../../web/kit';
import { mandiRef } from '../../lib/liveMarket';
import { Split } from '../../web/Split';

export default function S19_Quantity({ route, navigation }: { route: any; navigation: any }) {
  const { t, s, n, locale } = useSay();
  const qc = useQueryClient();
  const { crop, setSelectedCrop, selectedMandi, setSelectedMandi } = useMarket();
  const crops = useKnownCrops(); // only crops the server can price — a lot for anything else would be refused
  const photo: string | null = route.params?.photoUri ?? null;
  // The assistant's lot draft arrives as params (commodity, market, qty_kg): start from it.
  const draft = (route.params ?? {}) as { commodity?: string; market?: string; qty_kg?: number };
  const [kg, setKg] = useState(draft.qty_kg && draft.qty_kg >= 100 ? Math.round(draft.qty_kg / 100) * 100 : 1000);
  useEffect(() => {
    const c = draft.commodity && crops.find(x => x.name.toLowerCase() === draft.commodity!.toLowerCase());
    if (c) setSelectedCrop(c);
    if (draft.market) setSelectedMandi(draft.market);
    // Once, on arrival with a draft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.commodity, draft.market]);
  // A crop the server can't price (e.g. one picked on Home before the list loaded) can't be saved.
  const cropOk = crops.some(x => x.id === crop.id);
  const { mutate, isPending, isError } = useMutation({
    // A browser blob URL means nothing to a buyer's device and there is no upload endpoint yet, so it is not stored.
    mutationFn: () => createLot({ commodity_id: crop.name, market_id: mandiRef(selectedMandi), qty_kg: kg, harvest_date: new Date().toISOString().slice(0, 10) }),
    onSuccess: lot => { void qc.invalidateQueries({ queryKey: ['lots'] }); navigation.navigate('S20_QualityDiagnostic', { lot_id: lot.id }); },
  });
  const step = (d: number) => setKg(k => Math.max(100, Math.min(100_000, k + d)));
  return (
    <Split inApp photo={heroSrc(crop.name)} caption={cropName(crop, locale)} sub={t('qs_conversion', { kg: n(kg), bags: n(Math.floor(kg / 50)) })} title={s('काय आणि किती?', 'क्या और कितना?', 'What, and how much?')} step={3} of={5} speak={t('nar_scr_qty')}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S17_CameraGuide'))}>
      <div className="km-form">
        <div className="km-field"><b>{s('पीक', 'फसल', 'Crop')}</b>
          <div className="km-strip" style={{ marginTop: 0 }}><ul>{crops.map(c => <li key={c.id}><button className="km-tile" style={{ width: 106, height: 118 }} aria-pressed={c.id === crop.id} onClick={() => setSelectedCrop(c)}><img src={tileSrc(c.name)} alt="" /><span>{cropName(c, locale)}</span></button></li>)}</ul></div>
        </div>
        <div className="km-field"><b>{s('बाजार', 'मंडी', 'Market')}</b><div className="km-row" style={{ marginTop: 0 }}><PlacePickers light /></div></div>
        <div className="km-field"><b>{s('वजन', 'वज़न', 'Quantity')}</b>
          <div className="km-step"><button aria-label={s('कमी', 'कम', 'Less')} onClick={() => step(-100)}>−</button><output>{n(kg / 100)}<small>{t('qs_quintals')}</small></output><button aria-label={s('जास्त', 'ज़्यादा', 'More')} onClick={() => step(100)}>+</button></div>
          <div className="km-row" style={{ marginTop: 12 }}>{[5, 10, 25, 50].map(q => <button key={q} className="km-btn ghost" style={{ minHeight: 44, padding: '0 18px' }} onClick={() => setKg(q * 100)}>{n(q)}</button>)}</div>
        </div>
        {photo ? <p className="km-note">{s('फोटो अजून अपलोड होत नाही. खरेदीदाराला दिसणार नाही.', 'फोटो अभी अपलोड नहीं होती। खरीदार को नहीं दिखेगी।', 'Photo upload isn’t connected yet, so buyers won’t see it.')}</p> : null}
        {isError ? <p className="km-err" role="alert">{t('lot_create_error')}</p> : null}
        <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={isPending || !cropOk} onClick={() => mutate()}>{isPending ? t('qs_creating') : t('qs_create')}</button>
      </div>
    </Split>
  );
}
