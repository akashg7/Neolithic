import React from 'react';
import { createPortal } from 'react-dom';
import { useAgent } from '../../lib/agentContext';
import { sceneSrc, useSay } from '../../web/kit';

const HIDDEN = new Set(['Assistant', 'Menu', 'LanguageSwitcher']);

export function FloatingAssistant() {
  const { isOpen, open, screen } = useAgent();
  const { s } = useSay();
  if (isOpen || HIDDEN.has(screen.current_screen)) return null;
  return createPortal(
    <div className="km"><button className="km-fab" onClick={open}><img className="km-face" src={sceneSrc('crate')} alt="" />{s('कृषी मित्राला विचारा', 'कृषि मित्र से पूछें', 'Ask Krishi Mitr')}</button></div>,
    document.body,
  );
}
