import React, { useEffect, useState } from 'react';
import { translate } from '../../lib/i18n';
import { speakSmart, stopSpeaking } from '../../lib/voice';
import { Ic, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { Locale } from '../../types/api';

const OPTS: [Locale, string, string][] = [['mr', 'मराठी', 'मराठीत पुढे चला'], ['hi', 'हिन्दी', 'हिन्दी में आगे बढ़ें'], ['en', 'English', 'Continue in English']];

export default function S01_Language({ navigation }: { navigation: any }) {
  const { t, s, locale, setLocale } = useSay();
  const [playing, setPlaying] = useState<Locale | null>(null);
  useEffect(() => () => { void stopSpeaking(); }, []);
  const play = async (c: Locale) => {
    if (playing === c) { setPlaying(null); await stopSpeaking(); return; }
    setPlaying(c);
    try { await speakSmart(translate('splash_narration', c), c); } catch { /* no voice on this device */ }
    setPlaying(p => (p === c ? null : p));
  };
  return (
    <Split photo="walk" caption={s('तुमच्या भाषेत', 'आपकी भाषा में', 'In your language')} sub={t('lang_voice_title')} title={t('lang_heading')} lede={t('lang_heading_sub')} step={1} of={4}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S0_Splash'))} speak={t('lang_heading')}>
      <div className="km-form">
        <div className="km-opts" role="radiogroup">
          {OPTS.map(([c, name]) => (
            <div key={c} style={{ display: 'flex', gap: 10 }}>
              <button className="km-opt" role="radio" lang={c} aria-checked={locale === c} style={{ minHeight: 84 }} onClick={() => setLocale(c)}><b style={{ fontSize: 26, flex: 1 }}>{name}</b>{locale === c ? <Ic name="check-circle" size={26} color="var(--brand2)" /> : null}</button>
              <button className="km-back" style={{ width: 84, height: 84 }} onClick={() => play(c)} aria-label={`${t('lang_audio_preview')}: ${name}`}><Ic name={playing === c ? 'square' : 'volume'} size={24} color="var(--brand)" /></button>
            </div>
          ))}
        </div>
      </div>
      <div className="km-foot1"><button className="km-btn main" onClick={() => navigation.navigate('S1b_ValueCarousel')}>{OPTS.find(o => o[0] === locale)![2]}</button></div>
      <p className="km-note" style={{ marginTop: 14 }}>{t('lang_change_anytime')}</p>
    </Split>
  );
}
