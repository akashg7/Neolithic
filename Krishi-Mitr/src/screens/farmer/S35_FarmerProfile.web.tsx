import React from 'react';
import { useAuth } from '../../lib/auth';
import { marketLabel, useRefNames, useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S35_FarmerProfile({ navigation }: { navigation: any }) {
  useRefNames();
  const { t, s, locale } = useSay();
  const { user, signOut } = useAuth();
  return (
    <Split inApp photo="walk" caption={user?.name ?? ''} title={t('profile_title')} speak={t('nar_scr_profile')} onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S15_MyLots'))}>
      <div className="km-form">
        <dl className="km-costs" style={{ fontSize: 18, marginTop: 0 }}><div><dt>{t('fd_name_label')}</dt><dd>{user?.name}</dd></div><div><dt>{t('phone_mobile_label')}</dt><dd>{user?.phone}</dd></div>{user?.district_id && marketLabel(user.district_id, locale) ? <div><dt>{t('fd_district_label')}</dt><dd>{marketLabel(user.district_id, locale)}</dd></div> : null}</dl>
        <div className="km-foot1" style={{ marginTop: 0 }}><button className="km-btn main" onClick={() => navigation.getParent()?.getParent()?.navigate('LanguageSwitcher')}>{s('भाषा बदला', 'भाषा बदलें', 'Change language')}</button><button className="km-btn ghost" style={{ minHeight: 60 }} onClick={() => signOut()}>{t('root_sign_out')}</button></div>
        <p className="km-note">{t('profile_soon_land')}, {t('profile_soon_bank')}: {t('coming_soon')}</p>
      </div>
    </Split>
  );
}
