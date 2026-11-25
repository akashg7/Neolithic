/** Talks — website version of the farmer's offer inbox. */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ListenButton } from '../../components/ui/ListenButton';
import { WebFooter } from '../../components/web/WebFooter';
import { getLots, getOffers } from '../../lib/api';
import { formatQuintal, quintalValuePaise } from '../../lib/money';
import { Banner } from '../../web/Banner';
import { Empty, Skel, useSay } from '../../web/kit';
import { OfferRow } from '../../web/OfferRow';
import type { OfferDto } from '../../types/api';

export default function S37_Talks({ navigation }: { navigation: any }) {
  const { s, n, t, rs, locale } = useSay();
  const [f, setF] = useState<'all' | 'yours' | 'theirs' | 'new'>('all');
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['offers', 'talks'], queryFn: getOffers });
  const { data: lots } = useQuery({ queryKey: ['lots'], queryFn: getLots });
  const all = data ?? [];
  const mine = (o: OfferDto) => o.status === 'OPEN' && o.initiator !== 'FARMER';
  const sets = { all, yours: all.filter(mine), theirs: all.filter(o => o.status === 'OPEN' && !mine(o)), new: all.filter(o => o.status === 'OPEN' && o.round === 1) };
  const rows = [...sets[f]].sort((a, b) => Number(mine(b)) - Number(mine(a)) || b.created_at.localeCompare(a.created_at));
  const open = all.filter(o => o.status === 'OPEN');
  // "Best" is the best *buyer* bid waiting on him — never his own counter.
  const best = [...sets.yours].sort((a, b) => b.price_paise_per_qtl - a.price_paise_per_qtl)[0];
  const k = sets.yours.length;
  const sub = best
    ? s(`${n(k)} बोली तुमच्या उत्तराची वाट पाहत आहेत. सर्वात जास्त ${rs(best.price_paise_per_qtl)} प्रति क्विंटल.`, `${n(k)} बोली आपके जवाब के इंतज़ार में। सबसे ऊँची ${rs(best.price_paise_per_qtl)} प्रति क्विंटल।`, `${n(k)} ${k === 1 ? 'offer is' : 'offers are'} waiting for your reply. The highest is ${rs(best.price_paise_per_qtl)} per quintal.`)
    : open.length
      ? s('तुमचे उत्तर खरेदीदाराकडे आहे.', 'आपका जवाब खरीदार के पास है।', 'Your replies are with the buyers.')
      : all.length
        ? s('सध्या कोणतीही बोली उत्तराच्या प्रतीक्षेत नाही.', 'अभी कोई बोली जवाब के इंतज़ार में नहीं है।', 'No offers are waiting on you right now.')
        : t('chat_empty_title');

  return (
    <div className="km km-page">
      <Banner scene="yard" title={t('chat_title')} sub={sub}><ListenButton text={sub} /></Banner>
      <section className="km-wrap km-sec" style={{ maxWidth: 1060 }}>
        <div className="km-seg" role="group" style={{ marginBottom: 24, flexWrap: 'wrap' }}>
          {(['all', 'yours', 'theirs', 'new'] as const).map(k => <button key={k} aria-pressed={f === k} onClick={() => setF(k)}>{t(`chat_filter_${k}`, { n: n(sets[k].length) })}</button>)}
        </div>
        {isLoading ? <Skel h={220} /> : error && !data ? <Empty title={t('offers_fetch_error')} action={<button className="km-btn ghost" onClick={() => refetch()}>{t('chat_retry')}</button>} />
          : !rows.length ? <Empty title={t('chat_empty_title')} />
          : rows.map(o => (
            <OfferRow key={o.id} offer={o} lots={lots} state={mine(o) ? s('तुमचे उत्तर बाकी', 'आपका जवाब बाकी', 'Your reply needed') : t(`chat_status_${o.status.toLowerCase()}`)}>
              {o.status === 'OPEN' ? (
                <div className="km-row"><button className={mine(o) ? 'km-btn' : 'km-btn ghost'} onClick={() => navigation.navigate('S27_Bargaining', { offer_id: o.id })}>{mine(o) ? s('उत्तर द्या', 'जवाब दें', 'Reply to offer') : s('बोलणी पहा', 'बातचीत देखें', 'Open talk')}</button></div>
              ) : null}
            </OfferRow>
          ))}
        {sets.yours.length > 1 ? <p className="km-note" style={{ marginTop: 20 }}>{s(`सर्वात चांगली बोली स्वीकारल्यास ${formatQuintal(best!.qty_kg, locale)} क्विंटलचे ${rs(quintalValuePaise(best!.price_paise_per_qtl, best!.qty_kg))}.`, `सबसे अच्छी बोली मानने पर ${formatQuintal(best!.qty_kg, locale)} क्विंटल के ${rs(quintalValuePaise(best!.price_paise_per_qtl, best!.qty_kg))}।`, `Accepting the best offer pays ${rs(quintalValuePaise(best!.price_paise_per_qtl, best!.qty_kg))} for ${formatQuintal(best!.qty_kg, locale)} quintals.`)}</p> : null}
      </section>
      <WebFooter />
    </div>
  );
}
