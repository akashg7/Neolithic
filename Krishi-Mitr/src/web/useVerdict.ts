import { useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { recommendWindow } from '../lib/api';
import { useMarket } from './kit';
import type { WindowRecommendReq } from '../types/api';

let qty = 1000;
const subs = new Set<() => void>();
export const setVerdictQty = (kg: number) => { qty = Math.max(100, Math.min(100_000, kg)); subs.forEach(f => f()); };
export const useVerdictQty = () => useSyncExternalStore(f => { subs.add(f); return () => { subs.delete(f); }; }, () => qty);

/** Advice for the crop and market the farmer picked, and the quantity they set. */
export function useVerdict() {
  const m = useMarket();
  const kg = useVerdictQty();
  const c = m.o?.commodity.slug, k = m.o?.market.slug;
  const q = useQuery({
    queryKey: ['verdict', c, k, kg],
    enabled: !!c && !!k,
    placeholderData: p => p,
    queryFn: () => recommendWindow({ commodity_id: c!, market_id: k!, qty_kg: kg, grade: 'B', lot_id: null, horizon_days: 14 } as WindowRecommendReq),
  });
  return { ...m, kg, v: q.data, vLoading: m.loading || (q.isLoading && !!c), vFailed: m.failed || q.isError, vRefetch: () => { void m.refetch(); void q.refetch(); } };
}
