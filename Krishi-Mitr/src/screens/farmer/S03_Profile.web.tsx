import React, { useEffect, useState } from 'react';
import { VoiceMic } from '../../components/ui/VoiceMic';
import { ApiError, getDistricts, register } from '../../lib/api';
import { clearPendingAuth, getPendingAuth, useAuth } from '../../lib/auth';
import { clearOnboardingDraft, useOnboardingDraft } from '../../lib/onboardingDraft';
import { parseFarmerDetails } from '../../lib/parseFarmerDetails';
import { useSay } from '../../web/kit';
import { Split } from '../../web/Split';
import type { District } from '../../types/api';

export default function S03_Profile({ navigation, route }: { navigation: any; route?: any }) {
  const { t, s, locale } = useSay();
  const { signIn } = useAuth();
  const onboardingDraft = useOnboardingDraft();
  const [name, setName] = useState('');
  const [village, setVillage] = useState('');
  const [district, setDistrict] = useState('');
  const [districts, setDistricts] = useState<District[]>([]);
  const [heard, setHeard] = useState<string | null>(null);
  const [missed, setMissed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pending = getPendingAuth();
  // Mount only: a successful sign-up clears `pending` and must not bounce back here.
  useEffect(() => { if (!getPendingAuth()) navigation.replace('S2_Phone'); }, [navigation]);
  useEffect(() => { let off = false; getDistricts().then(l => { if (!off) setDistricts(l); }).catch(() => setError(t('network_error_generic'))); return () => { off = true; }; }, [t]);
  useEffect(() => {
    const rp = (route?.params ?? {}) as { name?: string; village?: string; district_id?: string };
    const nextName = onboardingDraft.name ?? rp.name;
    const nextVillage = onboardingDraft.village ?? rp.village;
    const nextDistrict = onboardingDraft.district_id ?? rp.district_id ?? onboardingDraft.district_name;
    if (nextName) setName(nextName);
    if (nextVillage) setVillage(nextVillage);
    if (nextDistrict && districts.length) {
      const match = districts.find(
        d =>
          d.id === nextDistrict ||
          d.name.toLowerCase() === String(nextDistrict).toLowerCase() ||
          d.name_mr === nextDistrict,
      );
      if (match) setDistrict(match.id);
    } else if (nextDistrict && String(nextDistrict).startsWith('dist_')) {
      setDistrict(String(nextDistrict));
    }
  }, [onboardingDraft, route?.params, districts]);
  const onVoice = (x: string) => {
    const p = parseFarmerDetails(x, districts);
    if (p.name) setName(p.name);
    if (p.districtId) setDistrict(p.districtId);
    if (p.village) setVillage(p.village);
    const got = !!(p.name || p.districtId || p.village);
    setHeard(got ? x : null); setMissed(!got);
  };
  const ok = name.trim().length > 0 && district !== '' && !busy;
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ok || !pending) return;
    setBusy(true); setError('');
    try {
      const res = await register({ phone: pending.phone, code: pending.code, name: name.trim(), role: pending.role, locale, district_id: district, ...(village.trim() ? { village: village.trim() } : {}) });
      clearPendingAuth();
      clearOnboardingDraft();
      await signIn(res);
    } catch (x) { setError(x instanceof ApiError ? x.message : t('network_error_generic')); setBusy(false); }
  };
  return (
    <Split photo="field" caption={s('एकदाच भरा', 'बस एक बार भरें', 'Fill this in once')} sub={t('fd_privacy_body')} title={t('fd_title')} lede={t('fd_hint')} step={4} of={4} speak={`${t('fd_title')}. ${t('fd_speak_sub')}`}
      onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('S2_Phone'))}>
      <form className="km-form" onSubmit={submit}>
        <div className="km-sheet"><b style={{ fontSize: 19 }}>{t('fd_speak_title')}</b><p className="km-mut">{t('fd_speak_example')}</p><VoiceMic locale={locale} onTranscript={onVoice} />
          {heard ? <p className="km-hint" style={{ marginTop: 10 }}>{t('fd_detected')}: {heard}</p> : null}{missed ? <p className="km-err" style={{ marginTop: 10 }}>{t('fd_not_understood')}</p> : null}</div>
        <div className="km-field"><label htmlFor="km-n">{t('fd_name_label')}</label><input id="km-n" className="km-in" autoComplete="name" value={name} placeholder={t('fd_name_placeholder')} onChange={e => setName(e.target.value)} /></div>
        <div className="km-opts two">
          <div className="km-field"><label htmlFor="km-d">{t('fd_district_label')}</label><select id="km-d" className="km-in" value={district} onChange={e => setDistrict(e.target.value)}><option value="">{s('निवडा', 'चुनें', 'Choose')}</option>{districts.map(d => <option key={d.id} value={d.id}>{locale === 'en' ? d.name : d.name_mr}</option>)}</select></div>
          <div className="km-field"><label htmlFor="km-v">{t('fd_village_label')}</label><input id="km-v" className="km-in" value={village} placeholder={t('fd_village_optional')} onChange={e => setVillage(e.target.value)} /></div>
        </div>
        {error ? <p className="km-err" role="alert">{error}</p> : null}
        <button className="km-btn" style={{ minHeight: 60, fontSize: 18 }} disabled={!ok}>{busy ? '…' : t('fd_submit')}</button>
        {!ok && !busy ? <p className="km-note">{t('fd_required')}</p> : null}
      </form>
    </Split>
  );
}
