import React from 'react';
import { noteText } from '../lib/offerNote';
import { formatQuintal, quintalValuePaise } from '../lib/money';
import { cropLabel, tileSrc, useSay } from './kit';
import type { LotDto, OfferDto } from '../types/api';

/** One offer or deal: crop photo, rate, total, and whatever the caller adds below. */
export function OfferRow({ offer, lots, state, children }: { offer: OfferDto; lots?: LotDto[]; state: string; children?: React.ReactNode }) {
  const { s, t, rs, day, locale } = useSay();
  const lot = lots?.find(l => offer.lots.some(x => String(x.lot_id) === l.id));
  const note = noteText(offer.note, t);
  return (
    <article className="km-deal">
      <img src={lot ? tileSrc(lot.commodity_id) : '/images/scene/crate.jpg'} alt="" loading="lazy" />
      <div className="b">
        <div className="top">
          <div>
            <h3 className="km-h2" style={{ fontSize: 22 }}>{lot ? cropLabel(lot.commodity_id, locale) : t('chat_from_buyer')}</h3>
            <p className="km-mut">{formatQuintal(offer.qty_kg, locale)} {s('क्विंटल', 'क्विंटल', 'quintals')}, {day(offer.created_at)}</p>
          </div>
          <span className="km-best" style={{ margin: 0, fontSize: 14 }}>{state}</span>
        </div>
        <dl className="km-facts">
          <div><dt>{t('bfl_rate_label')}</dt><dd style={{ fontSize: 24 }}>{rs(offer.price_paise_per_qtl)}</dd></div>
          <div><dt>{t('bfl_total_label')}</dt><dd style={{ fontSize: 24 }}>{rs(quintalValuePaise(offer.price_paise_per_qtl, offer.qty_kg))}</dd></div>
          {offer.status === 'OPEN' ? <div><dt>{s('फेरी', 'दौर', 'Round')}</dt><dd style={{ fontSize: 24 }}>{s(`३ पैकी ${offer.round}`, `3 में से ${offer.round}`, `${offer.round} of 3`)}</dd></div> : null}
        </dl>
        {note ? <p className="km-quote">{note}</p> : null}
        {children}
      </div>
    </article>
  );
}
