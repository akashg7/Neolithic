import React from 'react';
import { heroSrc, sceneSrc, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S01b_ValueCarousel({ navigation }: { navigation: any }) {
  const { t, s } = useSay();
  const next = () => navigation.navigate('S2_Phone');
  return (
    <Split photo="tea" caption={t('vc_refusal_title')} sub={t('vc_refusal_body')} title={t('vc_title')} step={2} of={4} speak={t('nar_scr_value')}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S1_Language'))}>
      <ul className="km-why">
        {[[heroSrc('onion'), 1], [sceneSrc('scale'), 2], [sceneSrc('truck'), 3]].map(([img, i]) => (
          <li key={i}><img src={img as string} alt="" /><div><b>{t(`vc_${i}_title`)}</b><span className="km-mut">{t(`vc_${i}_body`)}</span></div></li>
        ))}
      </ul>
      <div className="km-foot1"><button className="km-btn main" onClick={next}>{t('vc_next')}</button><button className="km-link" onClick={next}>{t('vc_login')}</button></div>
    </Split>
  );
}
