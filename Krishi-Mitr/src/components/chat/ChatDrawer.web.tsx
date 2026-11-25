import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useAgent } from '../../lib/agentContext';
import { ChatPanel } from './ChatPanel';

export function ChatDrawer() {
  const { isOpen, close, screen } = useAgent();
  useEffect(() => {
    if (!isOpen) return;
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && close();
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [isOpen, close]);
  if (!isOpen || screen.current_screen === 'Assistant') return null;
  return createPortal(<ChatPanel onClose={close} />, document.body);
}
