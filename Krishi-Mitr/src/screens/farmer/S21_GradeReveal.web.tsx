import React from 'react';
import { Empty, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { AssayReq, AssayRes } from '../../types/api';

const Q = ['size_uniform', 'colour_uniform', 'sprouting', 'moisture_feel', 'foreign_matter'] as const;

export default function S21_GradeReveal({ route, navigation }: { route: any; navigation: any }) {
  const { t, n, s } = useSay();
  const { result, answers, lot_id } = (route.params ?? {}) as { result?: AssayRes; answers?: AssayReq; lot_id?: string };
  if (!result || !answers) return <div className="km km-page"><div className="km-wrap km-sec"><Empty title={t('self_assay_error')} action={<button className="km-btn" onClick={() => navigation.navigate('S15_MyLots')}>{t('mp_title')}</button>} /></div></div>;
  const perfect = result.score >= 1000;
  const weak = result.weakest_dimension;
  const weakName = weak === 'damage_pct' ? t('assay_damage_question') : t(`assay_q_${weak}`);
  return (
    <Split inApp photo="hands" caption={perfect ? s('उत्तम माल', 'बढ़िया माल', 'Top quality') : t('gr_tip_title')} sub={perfect ? undefined : t(`tip_${weak}`)} title={t('gr_title')} step={4} of={5} speak={`${t('gr_narr_grade', { grade: result.grade, score: n(result.score) })} ${t(`tip_${weak}`)}`}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S15_MyLots'))}>
      <div className="km-form">
        <div style={{ display: 'flex', gap: 28, alignItems: 'center', flexWrap: 'wrap' }}><div className={`km-grade ${result.grade}`}>{result.grade}</div><div><div className="km-price" style={{ fontSize: 50 }}>{n(result.score)}<small style={{ color: 'var(--ink2)' }}>{t('gr_score_suffix')}</small></div>{perfect ? null : <p className="km-mut" style={{ marginTop: 8 }}>{t('gr_weakest_label')}: <b>{weakName}</b></p>}</div></div>
        <div><b>{t('gr_answers_title')}</b><dl className="km-costs" style={{ marginTop: 8 }}>{Q.map(k => <div key={k}><dt>{t(`assay_q_${k}`)}</dt><dd className={!perfect && weak === k ? 'km-bad' : ''}>{t(`assay_${k}_${answers[k]}`)}</dd></div>)}<div><dt>{t('assay_damage_question')}</dt><dd className={!perfect && weak === 'damage_pct' ? 'km-bad' : ''}>{n(answers.damage_pct)}%</dd></div></dl></div>
        <div className="km-foot1" style={{ marginTop: 0 }}><button className="km-btn main" onClick={() => navigation.navigate('S22_PricePublish', lot_id ? { lot_id } : undefined)}>{t('gr_cta_publish')}</button><button className="km-link" onClick={() => navigation.navigate('S20_QualityDiagnostic', { lot_id })}>{t('recheck_button')}</button></div>
        <p className="km-note">{s('ही तुमची स्वतःची तपासणी आहे. खरेदीदार वजनकाट्यावर पुन्हा तपासेल.', 'यह आपकी अपनी जाँच है। खरीदार काँटे पर फिर जाँचेगा।', 'This is your own check. The buyer re-checks it at the weighbridge.')}</p>
      </div>
    </Split>
  );
}
