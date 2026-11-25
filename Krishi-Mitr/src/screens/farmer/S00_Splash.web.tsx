/** Start: say what this is, pick a language, go. */
import React, { useState } from 'react';
import { Logo } from '../../components/ui/Logo';
import { ListenButton } from '../../components/ui/ListenButton';
import { useAuth } from '../../lib/auth';
import { enterDashboard } from '../../lib/api';
import { sceneSrc, useSay } from '../../web/kit';

export default function S00_Splash({ navigation }: { navigation: any }) {
  const { t, s, locale } = useSay();
  const { signIn } = useAuth();
  const [err, setErr] = useState(false);
  const demo = async () => { setErr(false); try { await signIn(await enterDashboard()); } catch { setErr(true); } };
  return (
    <div className="km km-page">
      <section className="km-hero" style={{ minHeight: '100%' }}>
        <img className="km-hero-img" src={sceneSrc('sunrise')} alt="" style={{ objectPosition: '60% 50%' }} />
        <div className="km-wrap" style={{ minHeight: '100dvh', paddingBlock: '28px 56px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'auto' }}>
            <button className="km-brand" style={{ color: '#fff' }} onClick={() => navigation.navigate('Web_Landing')}><Logo size={44} /><b>{t('splash_app_name')}</b></button>
            <ListenButton text={t('splash_narration')} />
          </div>
          <h1 lang={locale} style={{ maxWidth: '12ch', marginTop: 48 }}>{s('बोला. भाव ऐका. मग विका.', 'बोलिए। भाव सुनिए। फिर बेचिए।', 'Speak. Hear the rate. Then sell.')}</h1>
          <p style={{ fontSize: 20, maxWidth: '44ch', marginTop: 18, color: '#f4e3d8' }}>{t('splash_how_title')}</p>
          <div className="km-row" style={{ marginTop: 34 }}>
            <button className="km-btn" style={{ minHeight: 60, fontSize: 19 }} onClick={() => navigation.navigate('S1_Language')}>{t('splash_get_started')}</button>
            <button className="km-btn" data-glass style={{ minHeight: 60 }} onClick={() => navigation.navigate('S2_Phone')}>{t('splash_otp_login')}</button>
          </div>
          <div className="km-row" style={{ gap: 26 }}>
            <button className="km-link" style={{ color: '#fff' }} onClick={demo}>{s('डेमो पहा', 'डेमो देखें', 'View the demo')}</button>
            <button className="km-link" style={{ color: '#fff' }} onClick={() => navigation.navigate('Buyer_Splash')}>{t('splash_buyer_entry')}</button>
          </div>
          {err ? <p style={{ marginTop: 12, color: '#ffb59d' }}>{t('network_error_generic')}</p> : null}
        </div>
      </section>
    </div>
  );
}
