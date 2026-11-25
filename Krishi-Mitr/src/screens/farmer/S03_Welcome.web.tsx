/** Not on the sign-up path (register signs in directly); kept for its URL. No invented pass number, helpline or price. */
import React from 'react';
import { useAuth } from '../../lib/auth';
import { useSay } from '../../web/kit';
import { Split } from '../../web/Split';

export default function S03_Welcome({ navigation }: { navigation: any }) {
  const { t, s } = useSay();
  const { user } = useAuth();
  return (
    <Split photo="sunrise" caption={s('चला सुरू करूया', 'चलिए शुरू करें', 'Let’s begin')} title={user ? s(`स्वागत, ${user.name}`, `स्वागत, ${user.name}`, `Welcome, ${user.name}`) : s('स्वागत', 'स्वागत', 'Welcome')} lede={t('fd_hint')}>
      <div className="km-foot1"><button className="km-btn main" onClick={() => navigation.navigate('S2_Phone')}>{t('vc_next')}</button></div>
    </Split>
  );
}
