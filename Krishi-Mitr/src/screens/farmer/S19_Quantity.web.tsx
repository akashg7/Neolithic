/** What and how much. Supports both canonical slugs and names in draft params, and uploads captured lot photos. */
import React, { useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createLot, uploadLotPhoto } from '../../lib/api';
import { cropName, heroSrc, matchMarket, photoSlug, PlacePickers, tileSrc, useKnownCrops, useMarket, useRefData, useSay } from '../../web/kit';
import { mandiRef } from '../../lib/liveMarket';
import { STATIC_DISTRICTS, STATIC_MANDIS } from '../../lib/staticMarketData';
import { Split } from '../../web/Split';

export default function S19_Quantity({ route, navigation }: { route: any; navigation: any }) {
  const { t, s, n, locale } = useSay();
  const qc = useQueryClient();
  const { crop, setSelectedCrop, setSelectedDistrict, selectedMandi, setSelectedMandi } = useMarket();
  const crops = useKnownCrops(); // only crops the server can price — a lot for anything else would be refused
  const { commodities, districts, markets } = useRefData();
  const photo: string | null = route.params?.photoUri ?? null;
  const draft = (route.params ?? {}) as {
    commodity?: string;
    commodity_id?: string;
    market?: string;
    market_id?: string;
    qty_kg?: number;
  };
  const [kg, setKg] = useState(draft.qty_kg && draft.qty_kg >= 100 ? Math.round(draft.qty_kg / 100) * 100 : 1000);
  const appliedRef = useRef<string>('');

  const draftCrop = draft.commodity_id ?? draft.commodity;
  const draftMarket = draft.market_id ?? draft.market;
  const draftQty = typeof draft.qty_kg === 'number' && draft.qty_kg >= 100 ? Math.round(draft.qty_kg / 100) * 100 : undefined;

  useEffect(() => {
    if (!draftCrop && !draftMarket && draftQty == null) return;
    const refsReady = !draftMarket || !!(markets?.length && districts?.length);
    const sig = `${draftCrop ?? ''}|${draftMarket ?? ''}|${draftQty ?? ''}|${refsReady ? 1 : 0}`;
    if (appliedRef.current === sig) return;
    appliedRef.current = sig;

    if (draftCrop) {
      const refComm = commodities?.find(
        x => x.id === draftCrop || x.name.toLowerCase() === draftCrop.toLowerCase() || x.name_mr === draftCrop,
      );
      const targetName = refComm?.name ?? draftCrop;
      const slug = photoSlug(targetName);
      const c = crops.find(
        x =>
          x.id === draftCrop ||
          photoSlug(x.name) === slug ||
          x.name.toLowerCase() === targetName.toLowerCase() ||
          x.name_mr === draftCrop,
      );
      if (c) setSelectedCrop(c);
    }

    if (draftMarket) {
      const apiMkt = matchMarket(markets, draftMarket);
      if (apiMkt) {
        const dist = districts?.find(d => d.id === apiMkt.district_id);
        if (dist) setSelectedDistrict(dist.name);
        setSelectedMandi(apiMkt.name);
      } else {
        const clean = draftMarket.replace(/^mkt_/, '').toLowerCase();
        const staticMkt = STATIC_MANDIS.find(
          x => x.name.toLowerCase() === draftMarket.toLowerCase() || x.name.toLowerCase().includes(clean) || x.name_mr === draftMarket,
        );
        if (staticMkt) {
          const sd = STATIC_DISTRICTS.find(d => d.id === staticMkt.district_id);
          if (sd) setSelectedDistrict(sd.name);
          setSelectedMandi(staticMkt.name);
        } else {
          setSelectedMandi(draftMarket);
        }
      }
    }

    if (draftQty != null) setKg(draftQty);
  }, [draftCrop, draftMarket, draftQty, crops, commodities, districts, markets, setSelectedCrop, setSelectedDistrict, setSelectedMandi]);

  // A crop the server can't price (e.g. one picked on Home before the list loaded) can't be saved.
  const cropOk = crops.some(x => x.id === crop.id);
  const createdLotIdRef = useRef<string | null>(null);
  const { mutate, isPending, isError } = useMutation({
    mutationFn: async () => {
      const lot = createdLotIdRef.current
        ? { id: createdLotIdRef.current }
        : await createLot({
            commodity_id: crop.name,
            market_id: mandiRef(selectedMandi),
            qty_kg: kg,
            harvest_date: new Date().toISOString().slice(0, 10),
          });
      createdLotIdRef.current = lot.id;
      if (photo) {
        await uploadLotPhoto(lot.id, photo);
      }
      return lot;
    },
    onSuccess: lot => {
      createdLotIdRef.current = null;
      void qc.invalidateQueries({ queryKey: ['lots'] });
      navigation.navigate('S20_QualityDiagnostic', { lot_id: lot.id });
    },
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
        {photo ? (
          <div className="km-row" style={{ alignItems: 'center', gap: 12 }}>
            <img src={photo} alt="" style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 10 }} />
            <p className="km-hint">{s('फोटो लॉट सोबत सुरक्षित अपलोड होईल.', 'फोटो लॉट के साथ सुरक्षित अपलोड होगा।', 'Photo will be uploaded safely with this lot.')}</p>
          </div>
        ) : null}
        {isError ? <p className="km-err" role="alert">{t('lot_create_error')}</p> : null}
        <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={isPending || !cropOk} onClick={() => mutate()}>{isPending ? t('qs_creating') : t('qs_create')}</button>
      </div>
    </Split>
  );
}
