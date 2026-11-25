import React from 'react';
import { createPortal } from 'react-dom';
import { useAgent } from '../../lib/agentContext';
import { sceneSrc, useSay } from '../../web/kit';

// Steps keep their main button bottom-right, so the launcher shrinks to its photo there.
const MINI = /^S(13|17|18|19|20|21|22|23|30|32|33|35|38)_/;
const HIDDEN = new Set(['Assistant', 'Menu', 'LanguageSwitcher', 'Web_Landing', 'Buyer_Splash']);

export function FloatingAssistant() {
  const { isOpen, open, screen } = useAgent();
  const { s } = useSay();
  if (isOpen || HIDDEN.has(screen.current_screen)) return null;
  return createPortal(
    <div className="km"><button className={`km-fab${MINI.test(screen.current_screen) ? ' mini' : ''}`} aria-label={s('कृषी मित्राला विचारा', 'कृषि मित्र से पूछें', 'Ask Krishi Mitr')} onClick={open}><img className="km-face" src={sceneSrc('crate')} alt="" /><span>{s('कृषी मित्राला विचारा', 'कृषि मित्र से पूछें', 'Ask Krishi Mitr')}</span></button></div>,
    document.body,
  );
}
