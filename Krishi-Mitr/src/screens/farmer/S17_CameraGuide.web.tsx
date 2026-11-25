import React from 'react';
import { launchCamera, launchImageLibrary } from 'react-native-image-picker';
import { Ic, sceneSrc, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S17_CameraGuide({ navigation }: { navigation: any }) {
  const { t, s } = useSay();
  const take = (fn: typeof launchCamera) => fn({ mediaType: 'photo', saveToPhotos: false } as any, (r: any) => {
    const uri = r.assets?.[0]?.uri;
    if (!r.didCancel && !r.errorCode && uri) navigation.navigate('S18_PhotoReview', { photoUri: uri });
  });
  return (
    <Split inApp photo="phone" caption={s('चांगला फोटो, चांगली बोली', 'अच्छी फोटो, अच्छी बोली', 'A clear photo helps your bid')} title={t('cam_title')} lede={t('cam_skip_note')} step={1} of={5}
      onBack={() => navigation.navigate('S15_MyLots')} speak={t('nar_scr_camera')}>
      <ul className="km-why">
        {[['sunrise', 'cam_tip_light'], ['crate', 'cam_tip_fill'], ['mandi', 'cam_tip_spread']].map(([img, k]) => <li key={k}><img src={sceneSrc(img!)} alt="" /><b>{t(k!)}</b></li>)}
      </ul>
      <div className="km-foot1"><button className="km-btn main" onClick={() => take(launchCamera)}><Ic name="camera" />{t('cam_open')}</button><button className="km-btn ghost" style={{ minHeight: 60 }} onClick={() => take(launchImageLibrary as any)}>{s('फोटो निवडा', 'फोटो चुनें', 'Choose a photo')}</button></div>
      <div className="km-row"><button className="km-link" onClick={() => navigation.navigate('S19_Quantity', { photoUri: null })}>{t('cam_skip')}</button></div>
    </Split>
  );
}
