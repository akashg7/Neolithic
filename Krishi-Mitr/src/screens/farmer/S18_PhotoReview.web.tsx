import React from 'react';
import { useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S18_PhotoReview({ route, navigation }: { route: any; navigation: any }) {
  const { t, s } = useSay();
  const uri: string | null = route.params?.photoUri ?? null;
  return (
    <Split inApp photo="crate" caption={t('pr_question')} title={t('pr_title')} step={2} of={5} speak={t('nar_scr_photo')} onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S17_CameraGuide'))}>
      <div className="km-form">
        {uri ? <img className="km-photo" src={uri} alt={s('तुमचा फोटो', 'आपकी फोटो', 'Your photo')} /> : <p className="km-err">{t('pr_no_photo')}</p>}
        <div className="km-foot1" style={{ marginTop: 0 }}><button className="km-btn main" disabled={!uri} onClick={() => navigation.navigate('S19_Quantity', { photoUri: uri })}>{t('pr_use')}</button><button className="km-btn ghost" style={{ minHeight: 60 }} onClick={() => navigation.navigate('S17_CameraGuide')}>{t('pr_retake')}</button></div>
      </div>
    </Split>
  );
}
