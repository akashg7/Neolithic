/** Site header. Below 980px the five sections move to a bottom bar. */
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../lib/auth';
import { navigationRef } from '../../navigation/navigationRef';
import { Ic, useSay } from '../../web/kit';
import type { IconName } from '../ui/Icon';
import { Logo } from '../ui/Logo';
import type { Locale } from '../../types/api';

const TABS: [string, IconName, string][] = [
  ['Home', 'home', 'tab_home'], ['Prices', 'chart-bar', 'tab_market'], ['MyLots', 'box', 'tab_my_produce'],
  ['Talks', 'message-circle', 'tab_chat'], ['Deals', 'handshake', 'tab_deals'],
];
const ROOT: Record<string, string> = { Home: 'S4_Home', Prices: 'PricesIndex', MyLots: 'S15_MyLots', Talks: 'S37_Talks', Deals: 'S31_DealsList' };
const LANGS: [Locale, string][] = [['mr', 'मराठी'], ['hi', 'हिन्दी'], ['en', 'English']];

function activeTab(): string {
  if (!navigationRef.isReady()) return 'Home';
  const root = navigationRef.getRootState();
  const r: any = root?.routes[root.index];
  if (r?.name !== 'FarmerTabs') return '';
  return r.state ? r.state.routes[r.state.index ?? 0].name : r.params?.screen ?? 'Home';
}

export function WebNavbar() {
  const { user, signOut } = useAuth();
  const { t, locale, setLocale } = useSay();
  const [tab, setTab] = useState('Home');
  const [open, setOpen] = useState(false);
  const me = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sync = () => setTab(activeTab());
    const id = setTimeout(sync, 0);
    const off = navigationRef.addListener('state', sync);
    return () => { clearTimeout(id); off(); };
  }, []);
  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !me.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', close); };
  }, [open]);

  const go = (name: string, params?: object) => { setOpen(false); if (navigationRef.isReady()) (navigationRef as any).navigate(name, params); };

  return (
    <div className="km km-nav">
      <div className="km-wrap">
        <button className="km-brand" onClick={() => go('FarmerTabs', { screen: 'Home' })}><Logo size={38} /><span>{t('app_name')}</span></button>
        <nav className="km-tabs">
          {TABS.map(([name, icon, key]) => (
            <button key={name} aria-current={tab === name ? 'page' : undefined} onClick={() => go('FarmerTabs', { screen: name, params: { screen: ROOT[name], pop: true } })}>
              <Ic name={icon} size={22} />{t(key)}
            </button>
          ))}
        </nav>
        <div className="km-lang" role="group" aria-label={t('select_language')}>
          {LANGS.map(([c, label]) => <button key={c} lang={c} aria-pressed={locale === c} onClick={() => setLocale(c)}>{label}</button>)}
        </div>
        <div className="km-me" ref={me}>
          <button aria-expanded={open} aria-haspopup="menu" aria-label={user?.name ?? ''} onClick={() => setOpen(o => !o)}>
            <span className="km-ava">{(user?.name ?? '').trim().slice(0, 1) || '–'}</span><span>{user?.name}</span>
          </button>
          {open ? (
            <div className="km-menu" role="menu">
              <button role="menuitem" onClick={() => go('FarmerTabs', { screen: 'MyLots', params: { screen: 'S35_FarmerProfile' } })}><Ic name="edit" />{t('profile_title')}</button>
              <button role="menuitem" onClick={() => go('LanguageSwitcher')}><Ic name="globe" />{t('select_language')}</button>
              <button role="menuitem" onClick={() => go('Assistant')}><Ic name="message-circle" />{t('tab_assistant')}</button>
              <button role="menuitem" className="km-bad" onClick={() => { setOpen(false); signOut(); }}><Ic name="x-circle" />{t('root_sign_out')}</button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
