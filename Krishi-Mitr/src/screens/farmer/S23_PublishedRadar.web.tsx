import React from 'react';
import { useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S23_PublishedRadar({ route, navigation }: { route: any; navigation: any }) {
  const { t, rs } = useSay();
  const ask: number | undefined = route.params?.asking_paise;
  const home = () => navigation.reset({ index: 0, routes: [{ name: 'S15_MyLots' }] });
  return (
    <Split inApp photo="yard" caption={t('pub_sub')} title={t('pub_title')} speak={`${t('pub_title')} ${t('pub_sub')}`}>
      <div className="km-form">
        {ask ? <div><p className="km-mut">{t('pub_asking_label')}</p><div className="km-price">{rs(ask)}</div></div> : null}
        <div><b>{t('pub_next_title')}</b><ol style={{ margin: '10px 0 0', paddingLeft: 22, display: 'grid', gap: 10 }}>{[1, 2, 3].map(i => <li key={i}>{t(`pub_next_${i}`)}</li>)}</ol></div>
        <div className="km-foot1" style={{ marginTop: 0 }}><button className="km-btn main" onClick={home}>{t('pub_my_produce')}</button><button className="km-btn ghost" style={{ minHeight: 60 }} onClick={() => { home(); navigation.getParent()?.navigate('Talks'); }}>{t('pub_view_buyers')}</button></div>
      </div>
    </Split>
  );
}
