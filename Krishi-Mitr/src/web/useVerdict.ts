import { useEffect, useRef, useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { recommendWindow } from '../lib/api';
import { STATIC_CROPS, STATIC_DISTRICTS, STATIC_MANDIS } from '../lib/staticMarketData';
import { matchMarket, photoSlug, useKnownCrops, useMarket, useRefData } from './kit';
import type { WindowRecommendReq } from '../types/api';

let qty = 1000;
const subs = new Set<() => void>();
export const setVerdictQty = (kg: number) => { qty = Math.max(100, Math.min(100_000, kg)); subs.forEach(f => f()); };
export const useVerdictQty = () => useSyncExternalStore(f => { subs.add(f); return () => { subs.delete(f); }; }, () => qty);

export interface VerdictRouteParams {
  commodity_id?: string;
  commodity?: string;
  market_id?: string;
  market?: string;
  qty_kg?: number;
  lot_id?: string;
}

/** Advice for the crop and market picked on screen or passed via route params, and the quantity set. */
export function useVerdict(routeParams?: VerdictRouteParams) {
  const m = useMarket();
  const known = useKnownCrops();
  const { districts, markets } = useRefData();
  const kg = useVerdictQty();
  const appliedKeyRef = useRef<string>('');

  const pCrop = routeParams?.commodity_id ?? routeParams?.commodity;
  const pMarket = routeParams?.market_id ?? routeParams?.market;
  const pQty = typeof routeParams?.qty_kg === 'number' && routeParams.qty_kg >= 100
    ? Math.round(routeParams.qty_kg / 100) * 100
    : undefined;

  useEffect(() => {
    if (!pCrop && !pMarket && pQty == null) return;
    const refsReady = !pMarket || !!(markets?.length && districts?.length);
    const sig = `${pCrop ?? ''}|${pMarket ?? ''}|${pQty ?? ''}|${refsReady ? 1 : 0}`;
    if (appliedKeyRef.current === sig) return;
    appliedKeyRef.current = sig;

    if (pCrop) {
      const targetSlug = photoSlug(pCrop);
      const cropMatch =
        known.find(x => x.id === pCrop || photoSlug(x.name) === targetSlug || x.name.toLowerCase() === pCrop.toLowerCase()) ??
        STATIC_CROPS.find(x => x.id === pCrop || photoSlug(x.name) === targetSlug || x.name.toLowerCase() === pCrop.toLowerCase());
      if (cropMatch) m.setSelectedCrop(cropMatch);
    }

    if (pMarket) {
      const apiMkt = matchMarket(markets, pMarket);
      if (apiMkt) {
        const dist = districts?.find(d => d.id === apiMkt.district_id);
        if (dist) m.setSelectedDistrict(dist.name);
        m.setSelectedMandi(apiMkt.name);
      } else {
        const clean = pMarket.replace(/^mkt_/, '').toLowerCase();
        const staticMkt = STATIC_MANDIS.find(
          x => x.name.toLowerCase() === pMarket.toLowerCase() || x.name.toLowerCase().includes(clean) || x.name_mr === pMarket,
        );
        if (staticMkt) {
          const sd = STATIC_DISTRICTS.find(d => d.id === staticMkt.district_id);
          if (sd) m.setSelectedDistrict(sd.name);
          m.setSelectedMandi(staticMkt.name);
        }
      }
    }

    if (pQty != null) setVerdictQty(pQty);
  }, [pCrop, pMarket, pQty, known, markets, districts, m]);

  const c = m.o?.commodity.slug ?? pCrop;
  const k = m.o?.market.slug ?? pMarket;
  const q = useQuery({
    queryKey: ['verdict', c, k, kg],
    enabled: !!c && !!k,
    placeholderData: p => p,
    queryFn: () => recommendWindow({
      commodity_id: c!,
      market_id: k!,
      qty_kg: kg,
      grade: 'B',
      lot_id: routeParams?.lot_id ?? null,
      horizon_days: 14,
    } as WindowRecommendReq),
  });
  return {
    ...m,
    kg,
    v: q.data,
    vLoading: m.loading || (q.isLoading && !!c),
    vFailed: m.failed || q.isError,
    vRefetch: () => { void m.refetch(); void q.refetch(); },
  };
}
