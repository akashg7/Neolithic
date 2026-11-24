import React, { useState } from 'react';
import { VoiceMic } from '../../components/ui/VoiceMic';
import { ApiError, demoLogin, requestOtp } from '../../lib/api';
import { setPendingAuth, useAuth } from '../../lib/auth';
import { digitsFromSpeech } from '../../lib/spokenDigits';
import { USE_FIXTURES } from '../../config';
import { sceneSrc, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { Role } from '../../types/api';

export default function S02_Phone({ navigation }: { navigation: any }) {
  const { t, s, locale } = useSay();
  const { signIn } = useAuth();
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState<Role>('FARMER');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const ok = phone.length === 10;
  const fail = (e: unknown) => setError(e instanceof ApiError ? e.message : t('network_error_generic'));
  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ok || busy) return;
    setBusy(true); setError('');
    const full = `+91${phone}`;
    try { if (!USE_FIXTURES) await requestOtp(full); setPendingAuth(full, '', role); navigation.navigate('S3_OTP'); } catch (x) { fail(x); } finally { setBusy(false); }
  };
  return (
    <Split photo={role === 'FARMER' ? 'hands' : 'yard'} caption={role === 'FARMER' ? s('तुमचा माल, तुमचा भाव', 'आपका माल, आपका भाव', 'Your produce, your price') : s('थेट शेतातून खरेदी', 'सीधे खेत से खरीद', 'Buy straight from the farm')}
      title={s('तुमचा मोबाइल नंबर', 'आपका मोबाइल नंबर', 'Your mobile number')} lede={t('phone_subtitle')} step={3} of={4} speak={t('nar_scr_phone')}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S0_Splash'))}>
      <form className="km-form" onSubmit={send}>
        <div className="km-field"><b>{t('role_question')}</b>
          <div className="km-opts two" role="radiogroup">
            {([['FARMER', 'role_farmer', 'field'], ['BUYER', 'role_buyer', 'gate']] as const).map(([r, k, img]) => (
              <button type="button" key={r} className="km-opt photo" role="radio" aria-checked={role === r} onClick={() => setRole(r)}><img src={sceneSrc(img)} alt="" /><span><b>{t(k)}</b><small>{t(`${k}_sub`)}</small></span></button>
            ))}
          </div>
        </div>
        <div className="km-field"><label htmlFor="km-phone">{t('phone_mobile_label')}</label>
          <div className="km-tel"><span>+91</span><input id="km-phone" inputMode="numeric" autoComplete="tel-national" maxLength={10} value={phone} placeholder="98765 43210" onChange={e => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))} /></div>
        </div>
        <VoiceMic locale={locale} onTranscript={x => { const d = digitsFromSpeech(x, 10); if (d) setPhone(d); }} />
        {error ? <p className="km-err" role="alert">{error}</p> : null}
        <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={!ok || busy}>{busy ? t('phone_sending') : t('phone_get_otp')}</button>
        <p className="km-note"><b>{t('phone_privacy_bold')}</b> {t('phone_privacy_note')}</p>
        <button type="button" className="km-link" style={{ justifySelf: 'start' }} onClick={() => { setError(''); demoLogin('FARMER').then(signIn).catch(fail); }}>{s('नंबर न देता डेमो पहा', 'बिना नंबर डेमो देखें', 'View the demo without a number')}</button>
      </form>
    </Split>
  );
}
