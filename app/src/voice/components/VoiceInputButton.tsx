/**
 * Mandi-Setu Voice Module — VoiceInputButton Component (Track B: B7)
 * Interactive microphone button with:
 * - States: idle -> recording ("बोला...") -> processing (spinner) -> idle
 * - Max recording length: 10s auto-stop
 * - Graceful degradation to manual typing on any network or permission error
 */

import React from 'react';
import { useVoiceIn } from '../useVoiceIn';
import type { VoiceInputButtonProps } from '../types';

export const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  onResult,
  parseMode,
  fieldName,
  onError,
}) => {
  const { isListening, isProcessing, startListening, stopListening, error } = useVoiceIn(
    onResult,
    onError
  );

  const handleClick = () => {
    if (isProcessing) return;

    if (isListening) {
      stopListening();
    } else {
      startListening(parseMode, fieldName);
    }
  };

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
      <button
        type="button"
        onClick={handleClick}
        disabled={isProcessing}
        aria-label={isListening ? 'माइक बंद करा' : 'आवाजाने भरा'}
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: isListening ? '#EA4335' : isProcessing ? '#FBBC04' : '#107C41',
          color: '#FFFFFF',
          border: 'none',
          cursor: isProcessing ? 'wait' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
          boxShadow: isListening
            ? '0 0 0 8px rgba(234, 67, 53, 0.25)'
            : '0 4px 8px rgba(0,0,0,0.15)',
          transition: 'all 0.25s ease',
          animation: isListening ? 'pulse 1.5s infinite' : 'none',
        }}
      >
        {isProcessing ? '⏳' : isListening ? '⏹️' : '🎙️'}
      </button>

      <span style={{ fontSize: '12px', fontWeight: 600, color: isListening ? '#EA4335' : '#5F6368' }}>
        {isProcessing ? 'ओळखत आहे...' : isListening ? 'बोला...' : 'माइक दाबा'}
      </span>

      {error && (
        <span style={{ fontSize: '11px', color: '#D93025', maxWidth: '160px', textAlign: 'center' }}>
          {error} (टाइप करून भरा)
        </span>
      )}
    </div>
  );
};
