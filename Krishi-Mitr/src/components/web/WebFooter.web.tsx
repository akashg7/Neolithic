import React from 'react';
import { navigationRef } from '../../navigation/navigationRef';
import { useSay } from '../../web/kit';
import { Logo } from '../ui/Logo';

export function WebFooter() {
  const { s, t } = useSay();
  const go = (n: string, p?: object) => navigationRef.isReady() && (navigationRef as any).navigate(n, p);
  const tab = (x: string) => () => go('FarmerTabs', { screen: x });
  return (
    <footer className="km km-foot">
      <div className="km-wrap">
        <div className="km-brand" style={{ color: '#fff' }}><Logo size={36} /><b>{t('app_name')}</b></div>
        <nav>
          <button onClick={tab('Home')}>{t('tab_home')}</button><button onClick={tab('Prices')}>{t('tab_market')}</button><button onClick={tab('MyLots')}>{t('tab_my_produce')}</button><button onClick={tab('Talks')}>{t('tab_chat')}</button><button onClick={tab('Deals')}>{t('tab_deals')}</button><button onClick={() => go('Assistant')}>{t('tab_assistant')}</button><button onClick={() => go('LanguageSwitcher')}>{t('select_language')}</button>
        </nav>
        <p>{s('स्मार्ट इंडिया हॅकेथॉन २०२६, समस्या क्र. २६१३२. आधार क्रमांक साठवला जात नाही. छायाचित्रे प्रातिनिधिक आहेत.', 'स्मार्ट इंडिया हैकथॉन 2026, समस्या क्र. 26132. आधार नंबर नहीं रखा जाता। तस्वीरें सांकेतिक हैं।', 'Smart India Hackathon 2026, problem statement 26132. No Aadhaar numbers are stored. Photos are illustrative.')}</p>
      </div>
    </footer>
  );
}
