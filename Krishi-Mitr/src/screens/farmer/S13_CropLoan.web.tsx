import React from 'react';
import { formatBps } from '../../lib/money';
import { Empty, Skel, useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import { useVerdict } from '../../web/useVerdict';

export default function S13_CropLoan({ navigation }: { navigation: any }) {
  const { t, s, n, rs, locale } = useSay();
  const { v, vLoading, vRefetch } = useVerdict();
  const q = v?.pledge_quote;
  const gain = v?.expected_gain_paise ?? null;
  const left = q && gain != null ? gain - q.interest_paise : null;
  return (
    <Split inApp photo="store" caption={s('साठवा, पण पैसे आज हवेत?', 'रखें, पर पैसे आज चाहिए?', 'Storing, but need money now?')} sub={t('help_a_pledge')} title={t('loan_title')}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S9_Verdict'))} speak={q ? t('loan_narr_amount', { amount: rs(q.loan_paise), days: n(q.days), interest: rs(q.interest_paise) }) : t('loan_no_quote')}>
      <div className="km-form">
        {vLoading ? <Skel h={320} /> : !v ? <Empty title={t('verdict_error')} action={<button className="km-btn ghost" onClick={vRefetch}>{t('chat_retry')}</button>} /> : !q ? <Empty title={t('loan_no_quote')} body={t('loan_no_quote_sub')} /> : (
          <>
            <div><p className="km-mut">{t('loan_hero_label')}</p><div className="km-price">{rs(q.loan_paise)}</div><p className="km-mut" style={{ marginTop: 8 }}>{t('loan_hero_sub')}</p></div>
            <dl className="km-costs" style={{ fontSize: 17 }}>
              <div><dt>{t('loan_term_ltv')}</dt><dd>{formatBps(q.ltv_bps, locale)}</dd></div><div><dt>{t('loan_term_rate')}</dt><dd>{formatBps(q.rate_bps_annual, locale)}</dd></div>
              <div><dt>{t('loan_term_days')}</dt><dd>{t('loan_term_days_value', { days: n(q.days) })}</dd></div><div className="tot"><dt>{t('loan_term_interest')}</dt><dd>{rs(q.interest_paise)}</dd></div>
            </dl>
            {gain != null && left != null ? <><dl className="km-pair" style={{ marginTop: 0 }}><div><dt>{t('loan_compare_gain')}</dt><dd className="km-good">{rs(gain)}</dd></div><div><dt>{t('loan_compare_cost')}</dt><dd className="km-bad">{rs(q.interest_paise)}</dd></div></dl><p className={left > 0 ? 'km-hint' : 'km-err'}>{left > 0 ? t('loan_compare_verdict_good', { amount: rs(left) }) : t('loan_compare_verdict_bad')}</p></> : null}
            <div><b>{t('loan_how_title')}</b><p className="km-mut">{t('loan_how_body')}</p></div>
          </>
        )}
      </div>
    </Split>
  );
}
