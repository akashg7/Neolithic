import React from 'react';
import { formatQuintal } from '../lib/money';
import { cropLabel, marketLabel, tileSrc, useRefNames, useSay } from './kit';
import type { LotDto } from '../types/api';

/** A lot as a photo card. The photo is of the crop, not of this lot, so it carries no claim about it. */
export function LotCard({ lot, onOpen }: { lot: LotDto; onOpen: () => void }) {
  useRefNames();
  const { s, t, rs, locale } = useSay();
  const ask = (lot as LotDto & { expected_price_paise?: number }).expected_price_paise;
  return (
    <button className="km-lot" onClick={onOpen}>
      <figure>
        <img src={lot.photo_path ?? tileSrc(lot.commodity_id)} alt="" loading="lazy" />
        <span className="km-state">{t(`lot_status_${lot.status.toLowerCase()}`)}</span>
      </figure>
      <div className="b">
        <h3>{cropLabel(lot.commodity_id, locale)}</h3>
        <p className="km-mut">{marketLabel(lot.market_id, locale)}</p>
        <dl className="km-facts">
          <div><dt>{s('वजन', 'वज़न', 'Quantity')}</dt><dd>{formatQuintal(lot.qty_kg, locale)} {s('क्विं.', 'क्विं.', 'qtl')}</dd></div>
          <div><dt>{s('दर्जा', 'ग्रेड', 'Grade')}</dt><dd>{t(`lot_grade_${lot.grade.toLowerCase()}`)}</dd></div>
          {ask ? <div><dt>{s('मागणी', 'माँग', 'Asking')}</dt><dd>{rs(ask)}</dd></div> : null}
        </dl>
      </div>
    </button>
  );
}
