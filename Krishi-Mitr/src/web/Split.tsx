import React from 'react';
import { ListenButton } from '../components/ui/ListenButton';
import { Ic, sceneSrc, useSay } from './kit';

interface Props {
  photo: string; caption: string; sub?: string;
  title: string; lede?: string; step?: number; of?: number;
  onBack?: () => void; speak?: string; inApp?: boolean; children: React.ReactNode;
}
/** One task beside one photograph. Used by sign-up and by every selling step. */
export function Split({ photo, caption, sub, title, lede, step, of, onBack, speak, inApp, children }: Props) {
  const { t, locale } = useSay();
  return (
    <div className={`km km-page${inApp ? ' km-inapp' : ''}`}>
      <div className="km-split">
        <aside><div className="km-shot"><img key={photo} src={photo.startsWith('/') ? photo : sceneSrc(photo)} alt="" /><h2 lang={locale}>{caption}</h2>{sub ? <p>{sub}</p> : null}</div></aside>
        <main className="km-task">
          <div className="km-bar1">
            {onBack ? <button className="km-back" onClick={onBack} aria-label={t('back_button')}><Ic name="arrow-left" /></button> : null}
            {of ? <div className="km-prog" role="progressbar" aria-valuenow={step} aria-valuemax={of}>{Array.from({ length: of }, (_, i) => <i key={i} className={i < (step ?? 0) ? 'on' : ''} />)}</div> : <span style={{ flex: 1 }} />}
            {speak ? <ListenButton text={speak} /> : null}
          </div>
          <h1 lang={locale}>{title}</h1>
          {lede ? <p className="km-lede" style={{ fontSize: 18 }}>{lede}</p> : null}
          {children}
        </main>
      </div>
    </div>
  );
}
