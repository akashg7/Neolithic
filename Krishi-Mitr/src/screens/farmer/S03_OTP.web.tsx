import React, { useEffect, useRef, useState } from 'react';
import { VoiceMic } from '../../components/ui/VoiceMic';
import { ApiError, getDevOtp, requestOtp, verifyOtp } from '../../lib/api';
import { getPendingAuth, setPendingAuth, useAuth } from '../../lib/auth';
import { digitsFromSpeech } from '../../lib/spokenDigits';
import { USE_FIXTURES } from '../../config';
import { Ic, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S03_OTP({ navigation }: { navigation: any }) {
  const { t, s, n, locale } = useSay();
  const { signIn } = useAuth();
  const [code, setCode] = useState('');
  const [left, setLeft] = useState(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const boxes = useRef<(HTMLInputElement | null)[]>([]);
  const phone = getPendingAuth()?.phone ?? null;
  const role = getPendingAuth()?.role ?? 'FARMER';
  useEffect(() => { if (!phone) navigation.replace('S2_Phone'); else boxes.current[0]?.focus(); }, [phone, navigation]);
  useEffect(() => { if (left <= 0) return; const id = setTimeout(() => setLeft(x => x - 1), 1000); return () => clearTimeout(id); }, [left]);
  const back = () => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S2_Phone'));
  const put = (raw: string, i: number) => {
    const d = raw.replace(/\D/g, '');
    const next = d.length > 1 ? d.slice(0, 6) : (code.slice(0, i) + d + code.slice(i + 1)).slice(0, 6);
    setCode(next);
    boxes.current[Math.min(5, d.length > 1 ? next.length : i + (d ? 1 : 0))]?.focus();
  };
  const verify = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!phone || code.length !== 6 || busy) return;
    setBusy(true); setError('');
    try {
      if (USE_FIXTURES) { setPendingAuth(phone, code, role); navigation.navigate('S3_Profile'); return; }
      await signIn(await verifyOtp(phone, code));
    } catch (x) {
      if (x instanceof ApiError && x.status === 404) { setPendingAuth(phone, code, role); navigation.navigate('S3_Profile'); }
      else setError(x instanceof ApiError ? (x.status === 401 ? t('otp_invalid_expired') : x.message) : t('network_error_generic'));
    } finally { setBusy(false); }
  };
  const resend = async () => {
    if (!phone) return;
    setLeft(30); setError(''); setCode('');
    try { if (!USE_FIXTURES) await requestOtp(phone); } catch (x) { setError(x instanceof ApiError ? x.message : t('network_error_generic')); }
  };
  const dev = phone ? getDevOtp(phone) : null;
  return (
    <Split photo="phone" caption={s('फक्त एक कोड', 'बस एक कोड', 'Just one code')} sub={t('otp_footer')} title={t('otp_heading')} lede={t('otp_sent_to', { phone: phone ?? '' })} step={3} of={4} onBack={back} speak={t('otp_heading')}>
      <form className="km-form" onSubmit={verify}>
        <div className="km-otp">
          {Array.from({ length: 6 }, (_, i) => (
            <input key={i} ref={el => { boxes.current[i] = el; }} inputMode="numeric" autoComplete={i === 0 ? 'one-time-code' : 'off'} aria-label={`${t('otp_box_hint')} ${i + 1}`} value={code[i] ?? ''}
              onFocus={e => e.target.select()} onChange={e => put(e.target.value, i)}
              onKeyDown={e => { if (e.key === 'Backspace' && !code[i] && i > 0) { setCode(code.slice(0, i - 1)); boxes.current[i - 1]?.focus(); } }} />
          ))}
        </div>
        <VoiceMic locale={locale} onTranscript={x => { const d = digitsFromSpeech(x, 6); if (d) setCode(d); }} />
        {dev ? <button type="button" className="km-hint" onClick={() => setCode(dev.slice(0, 6))}><Ic name="info" />{s(`SMS अजून जोडलेले नाही. चाचणी कोड ${dev} भरा`, `SMS अभी जुड़ा नहीं है। टेस्ट कोड ${dev} भरें`, `SMS isn’t connected yet. Fill test code ${dev}`)}</button> : null}
        {error ? <p className="km-err" role="alert">{error}</p> : null}
        <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={code.length !== 6 || busy}>{busy ? t('otp_verifying') : t('otp_cta')}</button>
        <div className="km-row" style={{ marginTop: 0, justifyContent: 'space-between' }}>
          <button type="button" className="km-link" onClick={back}>{s('नंबर बदला', 'नंबर बदलें', 'Change number')}</button>
          {left > 0 ? <span className="km-note">{t('otp_resend_label')} {n(left)}s</span> : <button type="button" className="km-link" onClick={resend}>{t('otp_resend_btn')}</button>}
        </div>
      </form>
    </Split>
  );
}
