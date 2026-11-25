import React, { useState } from 'react';
import { useQueryClient, useMutation, useQuery } from '@tanstack/react-query';
import { getLot, submitAssay } from '../../lib/api';
import { formatQuintal } from '../../lib/money';
import { cropLabel, Empty, heroSrc, Skel, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { AssayReq } from '../../types/api';

const Q = ['size_uniform', 'colour_uniform', 'sprouting', 'moisture_feel', 'foreign_matter'] as const;

export default function S20_QualityDiagnostic({ route, navigation }: { route: any; navigation: any }) {
  const { t, n, locale } = useSay();
  const id: string | undefined = route.params?.lot_id;
  const { data: lot, isLoading, refetch } = useQuery({ queryKey: ['lots', id], queryFn: () => getLot(id!), enabled: !!id });
  const [a, setA] = useState<Partial<AssayReq>>({});
  const [i, setI] = useState(0);
  const qc = useQueryClient();
  const save = useMutation({ mutationFn: (b: AssayReq) => submitAssay(id!, b), onSuccess: (result, answers) => { void qc.invalidateQueries({ queryKey: ['lots'] }); navigation.navigate('S21_GradeReveal', { result, answers, lot_id: id }); } });
  const back = () => (i > 0 ? setI(i - 1) : navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S15_MyLots'));
  const key = Q[i];
  const pick = (v: 1 | 2 | 3) => { setA(x => ({ ...x, [key!]: v })); setI(i + 1); };
  const damage = a.damage_pct ?? 0;
  if (!id) return <div className="km km-page"><div className="km-wrap km-sec"><Empty title={t('lots_fetch_error')} action={<button className="km-btn" onClick={() => navigation.navigate('S15_MyLots')}>{t('mp_title')}</button>} /></div></div>;
  return (
    <Split inApp photo={lot ? heroSrc(lot.commodity_id) : 'crate'} caption={lot ? cropLabel(lot.commodity_id, locale) : t('qd_title')} sub={lot ? t('qty_label_value', { qty: formatQuintal(lot.qty_kg, locale) }) : undefined}
      title={key ? t(`assay_q_${key}`) : t('assay_damage_question')} lede={t('qd_answered', { done: n(i), total: n(6) })} step={i + 1} of={6} onBack={back}
      speak={key ? `${t(`assay_q_${key}`)} ${[3, 2, 1].map(v => t(`assay_${key}_${v}`)).join(', ')}` : t('assay_damage_question')}>
      {isLoading ? <Skel h={260} /> : !lot ? <Empty title={t('self_assay_error')} action={<button className="km-btn ghost" onClick={() => refetch()}>{t('chat_retry')}</button>} /> : key ? (
        <div className="km-form"><div className="km-opts" role="radiogroup" key={key}>{([3, 2, 1] as const).map(v => <button key={v} className="km-opt" role="radio" aria-checked={a[key] === v} style={{ minHeight: 80 }} onClick={() => pick(v)}><b>{t(`assay_${key}_${v}`)}</b></button>)}</div><p className="km-note">{t('qd_honest_note')}</p></div>
      ) : (
        <div className="km-form">
          <div className="km-step"><button aria-label="−5%" onClick={() => setA(x => ({ ...x, damage_pct: Math.max(0, damage - 5) }))}>−</button><output>{n(damage)}%</output><button aria-label="+5%" onClick={() => setA(x => ({ ...x, damage_pct: Math.min(100, damage + 5) }))}>+</button></div>
          {save.isError ? <p className="km-err" role="alert">{t('self_assay_save_error')}</p> : null}
          <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={save.isPending || Q.some(k => a[k] == null)} onClick={() => save.mutate({ ...(a as AssayReq), damage_pct: damage })}>{t('qd_cta')}</button>
          <p className="km-note">{t('qd_honest_note')}</p>
        </div>
      )}
    </Split>
  );
}
