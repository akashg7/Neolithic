/** Alerts from real data only: offers waiting, and this crop's weekly move. */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getOffers } from '../../lib/api';
import { formatQuintal } from '../../lib/money';
import { cropName, Empty, tileSrc, sceneSrc, useMarket, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S38_Notifications({ navigation }: { navigation: any }) {
  const { t, s, rs, locale } = useSay();
  const { crop, o } = useMarket();
  const { data } = useQuery({ queryKey: ['offers', 'talks'], queryFn: getOffers });
  const open = (data ?? []).filter(x => x.status === 'OPEN' && x.initiator === 'BUYER');
  const ch = o?.change_7d_paise_per_qtl ?? null;
  return (
    <Split inApp photo="tea" caption={t('nt_subtitle')} title={t('nt_title')} onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S4_Home'))}>
      <ul className="km-why">
        {open.map(x => <li key={x.id}><img src={sceneSrc('yard')} alt="" /><button onClick={() => navigation.getParent()?.navigate('Talks', { screen: 'S27_Bargaining', params: { offer_id: x.id } })}><b>{t('nt_offer_title')}</b><span className="km-mut">{rs(x.price_paise_per_qtl)}, {formatQuintal(x.qty_kg, locale)} {s('क्विंटल', 'क्विंटल', 'quintals')}</span></button></li>)}
        {ch ? <li><img src={tileSrc(crop.name)} alt="" /><button onClick={() => navigation.navigate('S4_Home')}><b>{cropName(crop, locale)} {ch > 0 ? t('nt_price_up_title') : t('nt_price_down_title')}</b><span className="km-mut">{s(`७ दिवसांत ${rs(Math.abs(ch))}`, `7 दिन में ${rs(Math.abs(ch))}`, `${rs(Math.abs(ch))} in 7 days`)}</span></button></li> : null}
      </ul>
      {!open.length && !ch ? <Empty title={t('nt_empty_title')} body={t('nt_empty_body')} /> : null}
    </Split>
  );
}
