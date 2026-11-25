/** Shared pieces for the website pages: data hook, formatting, photos, pickers. */
import React from 'react';
import { useQuery } from '@tanstack/react-query';

import './css';
import { Icon, IconName } from '../components/ui/Icon';
import { getAllMarkets, getCommodities, getDistricts, getMarketOverview, loadRefNames, MarketOverview, refLabel } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { District, Market } from '../types/api';
import { districtRef, mandiRef } from '../lib/liveMarket';
import { formatNumber, formatPaise } from '../lib/money';
import { STATIC_CROPS, STATIC_DISTRICTS, STATIC_MANDIS, StaticCrop } from '../lib/staticMarketData';
import { useStaticMarket } from '../lib/staticMarketStore';
import { useT } from '../lib/i18n';
import type { Locale } from '../types/api';

export type L3 = readonly [mr: string, hi: string, en: string];
export const pick = (l: Locale, v: L3) => (l === 'mr' ? v[0] : l === 'hi' ? v[1] : v[2]);

/** `s('मराठी','हिन्दी','English')` in the active language, plus formatters. */
export function useSay() {
  const { locale, setLocale, t } = useT();
  return {
    t,
    locale,
    setLocale,
    s: (mr: string, hi: string, en: string) => pick(locale, [mr, hi, en]),
    rs: (paise: number | null | undefined) => (paise == null ? '–' : formatPaise(paise, locale)),
    n: (v: number) => formatNumber(v, locale),
    day: (iso: string, opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' }) =>
      new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString(
        locale === 'en' ? 'en-IN' : `${locale}-IN-u-nu-deva`,
        opts,
      ),
  };
}

const named = (l: Locale, o: { name: string; name_mr: string; name_hi: string }) =>
  l === 'mr' ? o.name_mr : l === 'hi' ? o.name_hi : o.name;
export const cropName = (c: StaticCrop, l: Locale) => named(l, c);

/** Photo slug for a crop: `Bengal Gram` -> `chana`. Also accepts API slugs. */
const SLUGS: Record<string, string> = { 'bengal gram': 'chana', 'green chilli': 'chilli', gram: 'chana', chana: 'chana', bengal_gram: 'chana', green_chilli: 'chilli' };
export function photoSlug(nameOrId: string): string {
  const k = nameOrId.replace(/^cmd_/, '').toLowerCase();
  return SLUGS[k] ?? k;
}
/** Crop name from its id, in the active language, without waiting on the network. */
export function cropLabel(id: string, l: Locale): string {
  const c = STATIC_CROPS.find(x => photoSlug(x.name) === photoSlug(id));
  return c ? cropName(c, l) : refLabel(id, l);
}
/** Market name; blank rather than a raw id while names are loading. */
export function marketLabel(id: string, l: Locale): string {
  const v = refLabel(id, l);
  return v === id ? '' : v;
}
export const heroSrc = (c: string) => `/images/hero/${photoSlug(c)}.jpg`;
export const tileSrc = (c: string) => `/images/crops/${photoSlug(c)}.jpg`;
export const sceneSrc = (n: string) => `/images/scene/${n}.jpg`;

export function Ic({ name, size = 20, color = 'currentColor' }: { name: IconName; size?: number; color?: string }) {
  return <Icon name={name} size={size} color={color} />;
}

/** The picked crop + market, with the live overview from the API. */
export function useMarket() {
  useFollowUserDistrict();
  const m = useStaticMarket();
  // A remembered crop the server can't price (e.g. Sugarcane) falls back to one it can.
  const known = useKnownCrops();
  React.useEffect(() => {
    if (known.length && !known.some(c => c.id === m.selectedCrop.id)) m.setSelectedCrop(known[0]!);
  }, [known, m]);
  const crop = m.selectedCrop;
  const q = useQuery<MarketOverview>({
    queryKey: ['overview', crop.name, m.selectedMandi, m.selectedDistrict],
    queryFn: () => getMarketOverview(crop.name, mandiRef(m.selectedMandi), districtRef(m.selectedDistrict)),
    staleTime: 5 * 60_000,
    retry: 1,
  });
  return { ...m, crop, o: q.data, loading: q.isLoading, failed: q.isError, refetch: q.refetch };
}

export function useRefNames(): boolean {
  // Reading `data` is what subscribes the caller to the names arriving.
  return !!useQuery({ queryKey: ['refnames'], retry: 3,
    // loadRefNames swallows failures; surface them so the query retries.
    queryFn: async () => {
      await loadRefNames();
      if (refLabel('mkt_lasalgaon', 'en') === 'mkt_lasalgaon') throw new Error('reference names not loaded');
      return true;
    }, staleTime: Infinity }).data;
}

/** Server reference data (cached for the session). Lists the app offers come from here,
 *  so a farmer can only pick a crop, district or mandi the backend can price. */
export function useRefData() {
  const opts = { staleTime: Infinity, retry: 2 } as const;
  const commodities = useQuery({ queryKey: ['ref', 'commodities'], queryFn: getCommodities, ...opts }).data;
  const districts = useQuery({ queryKey: ['ref', 'districts'], queryFn: getDistricts, ...opts }).data;
  const markets = useQuery({ queryKey: ['ref', 'markets', 'all'], queryFn: getAllMarkets, ...opts }).data;
  return { commodities, districts, markets };
}

/** The app's crop tiles (photos, three-language names) limited to crops the server knows. */
export function useKnownCrops(): StaticCrop[] {
  const { commodities } = useRefData();
  if (!commodities) return STATIC_CROPS;
  const known = new Set(commodities.map(c => c.name.toLowerCase()));
  return STATIC_CROPS.filter(c => known.has(c.name.toLowerCase()));
}

const norm = (x: string) => x.toLowerCase().replace(/\s*(apmc|market committee|मुख्य बाजार समिती|बाजार समिती|मुख्य मंडी|मंडी)\s*/g, ' ').trim().split(/\s+/)[0] ?? '';

/** Find the server row a stored selection (English or Marathi, static or API spelling) refers to. */
export function matchDistrict(list: District[] | undefined, sel: string): District | undefined {
  if (!list) return undefined;
  const ref = districtRef(sel) ?? sel;
  return list.find(d => d.id === sel || d.name === ref || d.name_mr === sel || d.name === sel);
}
export function matchMarket(list: Market[] | undefined, sel: string): Market | undefined {
  if (!list) return undefined;
  const ref = mandiRef(sel);
  return list.find(m => m.id === sel || m.name === ref || m.name === sel || m.name_mr === sel)
    ?? list.find(m => norm(m.name) === norm(ref) || norm(m.name_mr) === norm(sel));
}
/** The mandi to show for a district: the app's usual one if the server has it, else its first. */
export function defaultMarketFor(markets: Market[] | undefined, district: District): Market | undefined {
  const inD = (markets ?? []).filter(m => m.district_id === district.id);
  const usual = STATIC_DISTRICTS.find(x => x.name === district.name);
  return (usual && matchMarket(inD, usual.defaultMandiEn)) ?? inD[0];
}

/**
 * Once per sign-in, start Home/Market on the farmer's own district (from his
 * profile) instead of the app default. Later picks are his and are left alone.
 */
let followedFor: string | null = null;
export function useFollowUserDistrict() {
  const { user } = useAuth();
  const { districts, markets } = useRefData();
  const m = useStaticMarket();
  React.useEffect(() => {
    const key = user ? `${user.id}:${user.district_id}` : null;
    if (!key || followedFor === key || !districts || !markets || !user?.district_id) return;
    followedFor = key;
    const d = districts.find(x => x.id === user.district_id);
    if (!d || matchDistrict(districts, m.selectedDistrict)?.id === d.id) return;
    const mk = defaultMarketFor(markets, d);
    m.setSelectedDistrict(d.name);
    if (mk) m.setSelectedMandi(mk.name);
  }, [user, districts, markets, m]);
}

export function CropStrip() {
  const { locale, s } = useSay();
  const { selectedCrop, setSelectedCrop } = useStaticMarket();
  const crops = useKnownCrops();
  return (
    <nav className="km-strip km-wrap" aria-label={s('पीक निवडा', 'फसल चुनें', 'Choose a crop')}>
      <ul>
        {crops.map(c => (
          <li key={c.id}>
            <button className="km-tile" aria-pressed={c.id === selectedCrop.id} onClick={() => setSelectedCrop(c)}>
              <img src={tileSrc(c.name)} alt="" loading="lazy" />
              <span>{cropName(c, locale)}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** District + mandi pickers over the server's reference data (19 districts, every mandi). */
export function PlacePickers({ light }: { light?: boolean }) {
  const { locale, s } = useSay();
  const { selectedDistrict, selectedMandi, setSelectedDistrict, setSelectedMandi } = useStaticMarket();
  const { districts, markets } = useRefData();
  const label = (x: { name: string; name_mr: string }) => (locale === 'en' ? x.name : x.name_mr || x.name);
  const cls = `km-pick${light ? ' light' : ''}`;
  if (!districts || !markets) return null;
  const d = matchDistrict(districts, selectedDistrict) ?? districts.find(x => x.name === 'Nashik') ?? districts[0]!;
  const inDistrict = markets.filter(x => x.district_id === d.id).sort((a, b) => a.name.localeCompare(b.name));
  const m = matchMarket(markets, selectedMandi);
  const options = m && !inDistrict.some(x => x.id === m.id) ? [m, ...inDistrict] : inDistrict;
  return (
    <>
      <span className={cls}>
        <select aria-label={s('जिल्हा', 'जिला', 'District')} value={d.id}
          onChange={e => {
            const x = districts.find(y => y.id === e.target.value);
            if (!x) return;
            setSelectedDistrict(x.name);
            const mk = defaultMarketFor(markets, x);
            if (mk) setSelectedMandi(mk.name);
          }}>
          {[...districts].sort((a, b) => a.name.localeCompare(b.name)).map(x => <option key={x.id} value={x.id}>{label(x)}</option>)}
        </select>
      </span>
      {options.length > 0 ? (
        <span className={cls}>
          <select aria-label={s('बाजार', 'मंडी', 'Market')} value={m?.id ?? ''}
            onChange={e => { const x = markets.find(y => y.id === e.target.value); if (x) setSelectedMandi(x.name); }}>
            {!m ? <option value="">{selectedMandi}</option> : null}
            {options.map(x => <option key={x.id} value={x.id}>{label(x)}</option>)}
          </select>
        </span>
      ) : null}
    </>
  );
}

export function sourceLine(o: MarketOverview, say: ReturnType<typeof useSay>): string {
  const d = say.day(o.latest.obs_date, { day: 'numeric', month: 'long', year: 'numeric' });
  return o.latest.source === 'AGMARKNET' || o.latest.source === 'MSAMB'
    ? say.s(`${o.latest.source}, ${d}`, `${o.latest.source}, ${d}`, `${o.latest.source}, ${d}`)
    : say.s(`संग्रहित अ‍ॅगमार्कनेट भाव, ${d}`, `संग्रहित एगमार्कनेट भाव, ${d}`, `Archived Agmarknet rate, ${d}`);
}

export type Verdict = { tone: 'hold' | 'sell' | 'none'; title: string };
export function verdictOf(action: string, days: number | null | undefined, say: Pick<ReturnType<typeof useSay>, 's' | 'n'>): Verdict {
  const d = say.n(days ?? 14);
  if (action === 'SPLIT') return { tone: 'hold', title: say.s(`अर्धे आज विका, अर्धे ${d} दिवस ठेवा`, `आधा आज बेचें, आधा ${d} दिन रखें`, `Sell half today, keep half for ${d} days`) };
  if (action === 'HOLD') return { tone: 'hold', title: say.s(`${d} दिवस थांबा`, `${d} दिन रुकें`, `Wait ${d} days`) };
  if (action === 'SELL_ELSEWHERE') return { tone: 'sell', title: say.s('दुसऱ्या बाजारात विका', 'दूसरी मंडी में बेचें', 'Sell at another market') };
  if (action === 'NO_ADVICE') return { tone: 'none', title: say.s('आज सल्ला देता येत नाही', 'आज सलाह नहीं दे सकते', 'We can’t advise today') };
  return { tone: 'sell', title: say.s('आजच विका', 'आज ही बेचें', 'Sell today') };
}

export function Empty({ title, body, action }: { title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="km-empty">
      <h3 className="km-h2" style={{ fontSize: 24 }}>{title}</h3>
      {body ? <p className="km-mut" style={{ margin: '8px auto 20px', maxWidth: '48ch' }}>{body}</p> : null}
      {action}
    </div>
  );
}
export const Skel = ({ h }: { h: number }) => <div className="km-skel" style={{ height: h }} aria-hidden />;
