/** The assistant, website version. One conversation, shown in the popover or full page. */
import React, { useEffect, useRef, useState } from 'react';
import { ListenButton } from '../ui/ListenButton';
import { transcribeAudio } from '../../lib/api';
import { useAgent } from '../../lib/agentContext';
import { STATIC_CROPS, STATIC_MANDIS } from '../../lib/staticMarketData';
import { useStaticMarket } from '../../lib/staticMarketStore';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';
import { cropName, heroSrc, Ic, sceneSrc, tileSrc, useSay, verdictOf } from '../../web/kit';
import type { AgentCard, ChatMessage } from '../../lib/agentTypes';

function useNames() {
  const { locale } = useSay();
  return {
    crop: (en: string) => { const c = STATIC_CROPS.find(x => x.name === en); return c ? cropName(c, locale) : en; },
    place: (en: string) => {
      if (locale === 'en') return en.replace(' APMC', '');
      const m = STATIC_MANDIS.find(x => x.name === en);
      return (m ? (locale === 'hi' ? m.name_hi : m.name_mr) : en).split(' ')[0]!;
    },
  };
}

function Spark({ v }: { v: number[] }) {
  if (v.length < 3) return null;
  const lo = Math.min(...v), sp = Math.max(...v) - lo || 1;
  const pts = v.map((x, i) => `${(i / (v.length - 1)) * 150},${42 - ((x - lo) / sp) * 36}`).join(' ');
  return <svg width="150" height="48" viewBox="-2 -2 156 50" aria-hidden><polyline points={pts} fill="none" stroke="var(--brand2)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function Card({ card }: { card: AgentCard }) {
  const say = useSay();
  const { s, rs, n, day } = say;
  const nm = useNames();
  const { runUiAction } = useAgent();
  const d = card.data;
  const head = (title: string, sub: string) => (
    <div className="ph"><img src={heroSrc(d.commodity)} alt="" /><div><b>{title}</b><span>{sub}</span></div></div>
  );
  if (card.type === 'WINDOW_VERDICT') {
    const w = card.data;
    const v = verdictOf(w.action, w.hold_days, say);
    return (
      <div className="km-card">
        {head(nm.crop(w.commodity), `${nm.place(w.mandi)}, ${n(w.quantity_kg)} ${s('किलो', 'किलो', 'kg')}`)}
        <div className="in">
          <div className={`km-verdict ${v.tone}`} style={{ fontSize: 24 }}>{v.title}</div>
          {w.action === 'NO_ADVICE' ? (
            w.uncertainty_pct != null ? <p className="km-mut">{s(`अनिश्चितता ${n(w.uncertainty_pct)}%`, `अनिश्चितता ${n(w.uncertainty_pct)}%`, `Uncertainty ${n(w.uncertainty_pct)}%`)}</p> : null
          ) : (
            <dl className="km-pair">
              <div><dt>{s('अपेक्षित नफा', 'अपेक्षित लाभ', 'Expected gain')}</dt><dd className={(w.expected_gain_paise ?? 0) >= 0 ? 'km-good' : 'km-bad'}>{rs(w.expected_gain_paise)}</dd></div>
              <div><dt>{s('सर्वात वाईट स्थिती', 'सबसे बुरी स्थिति', 'Worst case')}</dt><dd className={(w.worst_case_paise ?? 0) < 0 ? 'km-bad' : ''}>{rs(w.worst_case_paise)}</dd></div>
            </dl>
          )}
        </div>
      </div>
    );
  }
  if (card.type === 'PRICE_SNAPSHOT') {
    const w = card.data;
    return (
      <div className="km-card">
        {head(nm.crop(w.commodity), nm.place(w.mandi))}
        <div className="in" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: 12 }}>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-.02em', lineHeight: 1.1 }}>{rs(w.modal_price_paise_per_qtl)}</div>
            <p className="km-note">{w.obs_date ? `${w.source === 'ARCHIVE' ? s('संग्रहित', 'संग्रहित', 'Archived') : w.source}, ${day(w.obs_date)}` : w.source}</p>
          </div>
          <Spark v={w.series_paise_per_qtl} />
        </div>
      </div>
    );
  }
  const w = card.data;
  return (
    <div className="km-card">
      {head(nm.crop(w.commodity), s('लॉट मसुदा', 'लॉट मसौदा', 'Lot draft'))}
      <div className="in">
        <dl className="km-costs" style={{ marginTop: 0 }}>
          <div><dt>{s('वजन', 'वज़न', 'Quantity')}</dt><dd>{w.quantity_kg ? `${n(w.quantity_kg)} ${s('किलो', 'किलो', 'kg')}` : s('पुढे भरा', 'आगे भरें', 'Fill in next')}</dd></div>
          {w.mandi ? <div><dt>{s('बाजार', 'मंडी', 'Market')}</dt><dd>{nm.place(w.mandi)}</dd></div> : null}
        </dl>
        <button className="km-btn" style={{ width: '100%', marginTop: 14 }} onClick={() => runUiAction({ target_screen: 'S19_Quantity', params: { commodity: w.commodity, market: w.mandi, ...(w.quantity_kg ? { qty_kg: w.quantity_kg } : {}) } })}>{s('लॉट पूर्ण करा', 'लॉट पूरा करें', 'Finish the lot')}</button>
        <p className="km-note" style={{ marginTop: 8 }}>{s('अजून काहीही नोंदवले नाही.', 'अभी कुछ दर्ज नहीं हुआ।', 'Nothing is saved yet.')}</p>
      </div>
    </div>
  );
}

function Turn({ m }: { m: ChatMessage }) {
  const { t, s } = useSay();
  const { retry, runUiAction } = useAgent();
  if (m.role === 'user') return <div className="km-turn me">{m.text}</div>;
  if (m.role === 'error') return (
    <div className="km-turn"><p className="km-say">{t('chat_error')}</p><button className="km-link" onClick={() => retry(m.id)}>{t('chat_retry')}</button></div>
  );
  const r = m.response;
  return (
    <div className="km-turn">
      <p className="km-say">{r.reply_text}</p>
      {r.cards.map((c, i) => <Card key={i} card={c} />)}
      <div className="km-acts">
        {r.ui_action ? <button className="km-btn ghost" onClick={() => runUiAction(r.ui_action!)}>{r.ui_action.cta_label}</button> : null}
        <ListenButton text={r.reply_text} />
      </div>
      {r.citations.length ? <p className="km-note" style={{ marginTop: 8 }}>{s('स्रोत', 'स्रोत', 'Source')}: {r.citations.map(c => c.title).join(', ')}</p> : null}
    </div>
  );
}

export function ChatPanel({ onClose, bare }: { onClose?: () => void; bare?: boolean; closeIcon?: unknown }) {
  const { t, s, locale } = useSay();
  const { messages, isThinking, starters, send, reset } = useAgent();
  const { selectedCrop } = useStaticMarket();
  const [text, setText] = useState('');
  const [mic, setMic] = useState<'idle' | 'live' | 'busy'>('idle');
  const [micErr, setMicErr] = useState(false);
  const rec = useRef<any>(null);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { log.current?.scrollTo({ top: messages.length ? log.current.scrollHeight : 0, behavior: 'smooth' }); }, [messages.length, isThinking]);
  useEffect(() => { if (onClose) input.current?.focus(); return () => { rec.current?.stopRecorder().catch(() => {}); }; }, [onClose]);

  const submit = () => { const v = text.trim(); if (!v || isThinking) return; setText(''); void send(v); };
  const onMic = async () => {
    setMicErr(false);
    rec.current ??= new AudioRecorderPlayer();
    try {
      if (mic === 'idle') { await rec.current.startRecorder(); setMic('live'); return; }
      setMic('busy');
      const uri = await rec.current.stopRecorder();
      const { transcript } = await transcribeAudio(uri, locale);
      if (transcript.trim()) void send(transcript);
    } catch { setMicErr(true); }
    setMic('idle');
  };

  const last = messages[messages.length - 1];
  const chips = !isThinking && last?.role === 'assistant' ? last.response.quick_replies : [];
  const others = STATIC_CROPS.filter(c => c.id !== selectedCrop.id);
  const thumb = (i: number) => (i === 0 ? tileSrc(selectedCrop.name) : i === 1 ? sceneSrc('mandi') : i === 2 ? sceneSrc('truck') : tileSrc(others[i]!.name));

  return (
    <div className={`km km-chat${bare ? ' full' : ''}`} role={bare ? undefined : 'dialog'} aria-label={t('agent_title')}>
      <header>
        <img className="bgi" src={sceneSrc('field')} alt="" />
        <div style={{ flex: 1 }}><b>{t('agent_title')}</b><small>{s('मराठीत बोला किंवा लिहा', 'हिन्दी में बोलें या लिखें', 'Speak or type in English')}</small></div>
        {messages.length ? <button onClick={reset} aria-label={t('chat_new')} title={t('chat_new')}><Ic name="refresh" size={21} /></button> : null}
        {onClose ? <button onClick={onClose} aria-label={t('chat_close')} title={t('chat_close')}><Ic name="chevron-down" size={24} /></button> : null}
      </header>
      <div className="km-log" ref={log} aria-live="polite">
        {messages.length === 0 ? (
          <div>
            <p className="km-hello">{t('chat_greeting')}</p>
            <div className="km-asks">{starters.map((q, i) => <button key={q} onClick={() => send(q)}><img src={thumb(i)} alt="" />{q}</button>)}</div>
          </div>
        ) : messages.map(m => <Turn key={m.id} m={m} />)}
        {isThinking ? <div className="km-think" role="status"><i /><i /><i />{t('chat_thinking')}</div> : null}
      </div>
      {chips.length ? <div className="km-chips">{chips.map(c => <button key={c} onClick={() => send(c)}>{c}</button>)}</div> : null}
      {micErr ? <p className="km-note km-bad" style={{ padding: '0 20px 8px' }}>{t('chat_mic_error')}</p> : null}
      <form className="km-ask" onSubmit={e => { e.preventDefault(); submit(); }}>
        <textarea ref={input} rows={1} value={text} lang={locale}
          placeholder={mic === 'live' ? t('chat_listening') : mic === 'busy' ? t('chat_transcribing') : t('chat_placeholder')}
          aria-label={t('chat_placeholder')} onChange={e => setText(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }} />
        {text.trim()
          ? <button type="submit" className="km-rnd" disabled={isThinking} aria-label={t('chat_send')}><Ic name="arrow-right" size={22} /></button>
          : <button type="button" className={`km-rnd${mic === 'live' ? ' live' : ''}`} disabled={mic === 'busy' || isThinking} onClick={onMic} aria-label={mic === 'live' ? t('chat_mic_stop') : t('chat_mic_start')}><Ic name={mic === 'live' ? 'square' : 'mic'} size={22} /></button>}
      </form>
    </div>
  );
}
