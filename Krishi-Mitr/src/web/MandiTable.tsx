import React from 'react';
import type { MarketOverview } from '../lib/api';
import { useSay } from './kit';

type Row = MarketOverview['nearby']['rows'][number];

export function MandiTable({ rows }: { rows: Row[] }) {
  const { s, rs, n, locale } = useSay();
  if (!rows.length) return null;
  const nets = rows.map(r => r.net_paise_per_qtl);
  const max = Math.max(...nets), min = Math.min(...nets);
  return (
    <div className="km-tablewrap">
      <table>
        <thead>
          <tr>
            <th>{s('बाजार', 'मंडी', 'Market')}</th>
            <th>{s('अंतर', 'दूरी', 'Distance')}</th>
            <th className="km-hidem">{s('भाव', 'भाव', 'Rate')}</th>
            <th className="km-hidem">{s('वाहतूक', 'ढुलाई', 'Transport')}</th>
            <th>{s('हातात', 'हाथ में', 'Take home')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.market_id}>
              <td>
                <strong>{locale === 'en' ? (r.name ?? r.name_mr).replace(' APMC', '') : r.name_mr}</strong>
                {r.net_paise_per_qtl === max ? <span className="km-best">{s('सर्वात जास्त', 'सबसे ज़्यादा', 'Highest')}</span> : null}
              </td>
              <td>{n(Math.round(r.distance_km))} {s('किमी', 'किमी', 'km')}</td>
              <td className="km-hidem">{rs(r.gross_paise_per_qtl)}</td>
              <td className="km-hidem">{rs(r.transport_paise_per_qtl)}</td>
              <td>
                <strong>{rs(r.net_paise_per_qtl)}</strong>
                <span className="km-bar" aria-hidden style={{ width: `${30 + 70 * (max === min ? 1 : (r.net_paise_per_qtl - min) / (max - min))}px` }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
