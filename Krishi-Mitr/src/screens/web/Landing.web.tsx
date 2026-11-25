/** Front door. Same doors as before: farmer sign-up, farmer demo, buyer, buyer demo. */
import React, { useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { Logo } from '../../components/ui/Logo';
import { useAuth } from '../../lib/auth';
import { demoLogin } from '../../lib/api';
import { Ic, sceneSrc, tileSrc, useSay } from '../../web/kit';
import type { Locale } from '../../types/api';

const LANGS: [Locale, string][] = [['mr', 'मराठी'], ['hi', 'हिन्दी'], ['en', 'English']];

export default function Landing() {
  const nav = useNavigation<{ navigate: (s: string) => void }>();
  const { signIn } = useAuth();
  const { s, t, locale, setLocale } = useSay();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const demo = async (role: 'FARMER' | 'BUYER') => {
    setBusy(true); setErr(false);
    try { await signIn(await demoLogin(role)); } catch { setErr(true); }
    setBusy(false);
  };
  const rules: [string, string, string][] = [
    ['pomegranate', s('नफा आणि तोटा, दोन्ही सारख्याच ठळक', 'लाभ और नुकसान, दोनों बराबर साफ', 'Gain and loss, equally plain'), s('किती मिळू शकते आणि किती जाऊ शकते, दोन्ही एकाच आकारात दिसते.', 'कितना मिल सकता है और कितना जा सकता है, दोनों एक ही आकार में दिखते हैं।', 'What you may earn and what you may lose are shown at the same size.')],
    ['wheat', s('खात्री नसेल तर सल्ला नाही', 'पक्का न हो तो सलाह नहीं', 'No guesswork'), s('भावात फार चढ-उतार असेल तर ॲप स्पष्ट सांगते की सल्ला देता येत नाही.', 'भाव में बहुत उतार-चढ़ाव हो तो ऐप साफ कहता है कि सलाह नहीं दे सकते।', 'When rates swing too much, the app says it cannot advise.')],
    ['chilli', s('वाचायची गरज नाही', 'पढ़ने की ज़रूरत नहीं', 'You don’t have to read'), s('भाव आणि सल्ला तुमच्या भाषेत ऐका.', 'भाव और सलाह अपनी भाषा में सुनें।', 'Listen to rates and advice in your language.')],
  ];
  return (
    <div className="km km-page">
      <section className="km-hero">
        <img className="km-hero-img" src={sceneSrc('mandi')} alt="" />
        <div className="km-wrap" style={{ paddingBlock: '24px 72px', minHeight: 'clamp(600px,86vh,820px)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 'auto', flexWrap: 'wrap' }}>
            <span className="km-brand" style={{ color: '#fff', marginRight: 'auto' }}><Logo size={40} /><b>{t('app_name')}</b></span>
            <div className="km-lang" style={{ background: 'rgba(255,255,255,.12)', borderRadius: 10, padding: 3 }}>
              {LANGS.map(([c, l]) => <button key={c} lang={c} aria-pressed={locale === c} style={locale === c ? undefined : { color: '#fff' }} onClick={() => setLocale(c)}>{l}</button>)}
            </div>
          </div>
          <h1 lang={locale} style={{ maxWidth: '10ch', marginTop: 56 }}>{s('आज विकू की थांबू?', 'आज बेचूँ या रुकूँ?', 'Sell today, or wait?')}</h1>
          <p style={{ fontSize: 20, maxWidth: '46ch', marginTop: 20, color: '#f4e3d8' }}>{s('वाहतूक, आडत आणि हमाली वजा करून हातात किती येईल ते पहा. मग ठरवा.', 'ढुलाई, आढ़त और हमाली घटाकर हाथ में कितना आएगा, देखें। फिर तय करें।', 'See what you take home after transport, commission and loading. Then decide.')}</p>
          <div className="km-row" style={{ marginTop: 32 }}>
            <button className="km-btn" style={{ minHeight: 58, fontSize: 18 }} onClick={() => nav.navigate('S0_Splash')}>{s('मी शेतकरी आहे', 'मैं किसान हूँ', 'I’m a farmer')}</button>
            <button className="km-btn" style={{ minHeight: 58, fontSize: 18, background: 'rgba(255,255,255,.14)' }} disabled={busy} data-glass onClick={() => demo('FARMER')}>{s('डेमो पहा', 'डेमो देखें', 'View the demo')}</button>
          </div>
          {err ? <p style={{ marginTop: 14, color: '#ffb59d' }}>{s('सर्व्हरशी जोडता आले नाही. थोड्या वेळाने पुन्हा पहा.', 'सर्वर से जुड़ नहीं पाए। थोड़ी देर बाद फिर देखें।', 'Couldn’t reach the server. Try again in a moment.')}</p> : null}
        </div>
      </section>
      <section className="km-wrap km-sec">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(270px,1fr))', gap: 'clamp(24px,3vw,44px)' }}>
          {rules.map(([img, h, p]) => (
            <div key={img}><img src={tileSrc(img)} alt="" style={{ width: '100%', aspectRatio: '4/3', objectFit: 'cover', borderRadius: 18 }} /><h2 className="km-h2" style={{ fontSize: 24, marginTop: 20 }}>{h}</h2><p className="km-lede">{p}</p></div>
          ))}
        </div>
      </section>
      <section className="km-banner">
        <img src={sceneSrc('truck')} alt="" />
        <div className="km-wrap" style={{ paddingBlock: 64 }}>
          <h2 style={{ fontSize: 'clamp(30px,3.6vw,48px)', fontWeight: 800, letterSpacing: '-.025em' }}>{s('माल खरेदी करता?', 'माल खरीदते हैं?', 'Buying produce?')}</h2>
          <p>{s('प्रतवारी केलेले लॉट शोधा, थेट बोली द्या, एस्क्रोमधून पैसे द्या.', 'ग्रेड किए लॉट खोजें, सीधे बोली दें, एस्क्रो से भुगतान करें।', 'Find graded lots, bid directly, and pay through escrow.')}</p>
          <div className="km-row">
            <button className="km-btn" onClick={() => nav.navigate('Buyer_Splash')}>{s('खरेदीदार म्हणून सुरू करा', 'खरीदार के रूप में शुरू करें', 'Start as a buyer')}</button>
            <button className="km-link" style={{ color: '#fff' }} disabled={busy} onClick={() => demo('BUYER')}>{s('खरेदीदार डेमो', 'खरीदार डेमो', 'Buyer demo')}</button>
          </div>
        </div>
      </section>
      <footer className="km-wrap" style={{ paddingBlock: 28, display: 'flex', gap: 12, alignItems: 'center', color: 'var(--ink2)', fontSize: 15 }}>
        <Ic name="shield-check" /> {s('स्मार्ट इंडिया हॅकेथॉन २०२६, समस्या क्र. २६१३२. आधार क्रमांक साठवला जात नाही.', 'स्मार्ट इंडिया हैकथॉन 2026, समस्या क्र. 26132. आधार नंबर नहीं रखा जाता।', 'Smart India Hackathon 2026, problem statement 26132. No Aadhaar numbers are stored.')}
      </footer>
    </div>
  );
}
