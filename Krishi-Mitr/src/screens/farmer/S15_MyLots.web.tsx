/** My produce — website version of S15: totals, every lot, add a lot. */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ListenButton } from '../../components/ui/ListenButton';
import { WebFooter } from '../../components/web/WebFooter';
import { getLots } from '../../lib/api';
import { formatQuintal } from '../../lib/money';
import { Banner } from '../../web/Banner';
import { Empty, Ic, Skel, useSay } from '../../web/kit';
import { LotCard } from '../../web/LotCard';

export default function S15_MyLots({ navigation }: { navigation: any }) {
  const { s, n, t, locale } = useSay();
  const { data: lots, isLoading, error, refetch } = useQuery({ queryKey: ['lots'], queryFn: getLots });
  const add = () => navigation.navigate('S17_CameraGuide');
  const kg = (lots ?? []).reduce((a, l) => a + l.qty_kg, 0);
  const total = s(`${n(lots?.length ?? 0)} लॉट, एकूण ${formatQuintal(kg, locale)} क्विंटल (${n(Math.floor(kg / 50))} गोण्या)`, `${n(lots?.length ?? 0)} लॉट, कुल ${formatQuintal(kg, locale)} क्विंटल (${n(Math.floor(kg / 50))} बोरी)`, `${n(lots?.length ?? 0)} ${(lots?.length ?? 0) === 1 ? 'lot' : 'lots'}, ${formatQuintal(kg, locale)} quintals in all (${n(Math.floor(kg / 50))} bags)`);

  return (
    <div className="km km-page">
      <Banner scene="store" title={t('mp_title')} sub={lots?.length ? total : undefined}>
        <button className="km-btn" onClick={add}><Ic name="plus" />{s('शेतमाल नोंदवा', 'उपज जोड़ें', 'Add produce')}</button>
        <ListenButton text={lots?.length ? total : t('mp_empty_title')} />
      </Banner>
      <section className="km-wrap km-sec">
        {isLoading ? <div className="km-lots">{[0, 1, 2].map(i => <Skel key={i} h={340} />)}</div>
          : error && !lots ? <Empty title={t('lots_fetch_error')} action={<button className="km-btn ghost" onClick={() => refetch()}>{t('chat_retry')}</button>} />
          : !lots?.length ? <Empty title={t('produce_empty_heading')} body={t('lots_empty_description')} action={<button className="km-btn" onClick={add}>{t('produce_cta_list')}</button>} />
          : (
            <div className="km-lots">
              {lots.map(l => <LotCard key={l.id} lot={l} onOpen={() => navigation.navigate('S20_QualityDiagnostic', { lot_id: l.id })} />)}
              <button className="km-lot km-add" onClick={add}><Ic name="plus" size={30} color="var(--brand2)" /><b>{t('mp_add_another')}</b><span className="km-mut">{t('mp_add_another_sub')}</span></button>
            </div>
          )}
      </section>
      <WebFooter />
    </div>
  );
}
