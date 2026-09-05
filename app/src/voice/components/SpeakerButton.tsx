/**
 * Mandi-Setu Voice Module — SpeakerButton Component (Track A: Voice-OUT)
 * Reusable "🔊 पुन्हा ऐका" button with auto-play on mount and graceful error handling.
 */

import React, { useEffect, useState } from 'react';
import { useVoiceOut } from '../useVoiceOut';
import type { SpeakerButtonProps } from '../types';

export const SpeakerButton: React.FC<SpeakerButtonProps> = ({
  text,
  autoPlayOnMount = false,
  size = 'medium',
  onPlayStart,
  onPlayEnd,
  onError,
}) => {
  const { speak, stop, isPlaying, isLoading, error } = useVoiceOut();
  const [hasPlayedOnce, setHasPlayedOnce] = useState(false);

  useEffect(() => {
    if (autoPlayOnMount && text) {
      handlePress();
    }
    return () => {
      stop();
    };
  }, [text, autoPlayOnMount]);

  useEffect(() => {
    if (error && onError) {
      onError(new Error(error));
    }
  }, [error, onError]);

  const handlePress = async () => {
    if (isPlaying) {
      stop();
      return;
    }
    if (onPlayStart) onPlayStart();
    try {
      await speak(text);
      setHasPlayedOnce(true);
      if (onPlayEnd) onPlayEnd();
    } catch (err: any) {
      if (onError) onError(err);
    }
  };

  const label = isPlaying
    ? 'थांबवा'
    : hasPlayedOnce
    ? 'पुन्हा ऐका'
    : 'ऐका';

  return (
    <button
      type="button"
      onClick={handlePress}
      disabled={isLoading}
      aria-label={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        padding: size === 'small' ? '6px 12px' : size === 'large' ? '12px 24px' : '8px 16px',
        borderRadius: '24px',
        backgroundColor: isPlaying ? '#E6F4EA' : '#107C41',
        color: isPlaying ? '#137333' : '#FFFFFF',
        border: '1px solid #107C41',
        fontSize: size === 'small' ? '13px' : size === 'large' ? '16px' : '14px',
        fontWeight: 600,
        cursor: isLoading ? 'wait' : 'pointer',
        boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
        transition: 'all 0.2s ease',
      }}
    >
      {isLoading ? (
        <span>⏳ लोड होत आहे...</span>
      ) : (
        <>
          <span style={{ fontSize: size === 'large' ? '20px' : '16px' }}>
            {isPlaying ? '⏹️' : '🔊'}
          </span>
          <span>{label}</span>
        </>
      )}
      {error && !isLoading && !isPlaying && (
        <span style={{ color: '#D93025', fontSize: '12px', marginLeft: '4px' }} title={error}>
          ⚠️
        </span>
      )}
    </button>
  );
};
