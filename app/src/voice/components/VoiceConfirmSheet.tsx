/**
 * Mandi-Setu Voice Module — VoiceConfirmSheet Component (Track B: B8)
 * Human confirmation sheet for voice-filled fields.
 * HARD INVARIANT: Voice never commits data; farmer MUST tap "बरोबर आहे" (onConfirm).
 */

import React from 'react';
import type { VoiceConfirmSheetProps } from '../types';

export const VoiceConfirmSheet: React.FC<VoiceConfirmSheetProps> = ({
  parsedFields,
  onConfirm,
  onEdit,
  onCancel,
}) => {
  const entries = Object.entries(parsedFields);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#FFFFFF',
        borderTopLeftRadius: '20px',
        borderTopRightRadius: '20px',
        boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.15)',
        padding: '24px 20px',
        zIndex: 1000,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        maxWidth: '540px',
        margin: '0 auto',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '18px', color: '#202124', fontWeight: 700 }}>
            माहितीची खात्री करा
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#5F6368' }}>
            आवाजाने भरलेली माहिती तपासा आणि पुष्टी करा
          </p>
        </div>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            style={{ border: 'none', background: 'none', fontSize: '20px', cursor: 'pointer', color: '#70757A' }}
          >
            ✕
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
        {entries.map(([key, item]) => {
          const isHighConfidence = item.confidence >= 0.8;
          const displayLabel = item.label_mr || key;

          return (
            <div
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 14px',
                backgroundColor: '#F8F9FA',
                borderRadius: '10px',
                border: isHighConfidence ? '1px solid #E8EAED' : '1px solid #F9AB00',
              }}
            >
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: '12px', color: '#5F6368', textTransform: 'capitalize' }}>
                  {displayLabel}
                </span>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#202124', marginTop: '2px' }}>
                  {item.value || <span style={{ color: '#D93025', fontStyle: 'italic' }}>रिकामा (भरला नाही)</span>}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: '12px',
                    backgroundColor: isHighConfidence ? '#E6F4EA' : '#FEF7E0',
                    color: isHighConfidence ? '#137333' : '#B06000',
                  }}
                >
                  {isHighConfidence ? '✓ खात्रीशीर' : '⚠ तपासून घ्या'}
                </span>

                <button
                  type="button"
                  onClick={() => onEdit(key)}
                  style={{
                    backgroundColor: 'transparent',
                    border: '1px solid #DADCE0',
                    borderRadius: '6px',
                    padding: '5px 10px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    color: '#1A73E8',
                    fontWeight: 500,
                  }}
                >
                  बदला
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Primary Commit Point */}
      <button
        type="button"
        onClick={onConfirm}
        style={{
          width: '100%',
          padding: '14px',
          backgroundColor: '#107C41',
          color: '#FFFFFF',
          border: 'none',
          borderRadius: '10px',
          fontSize: '16px',
          fontWeight: 700,
          cursor: 'pointer',
          boxShadow: '0 2px 6px rgba(16, 124, 65, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
        }}
      >
        <span>✓</span>
        <span>हो, बरोबर आहे (पुष्टी करा)</span>
      </button>
    </div>
  );
};
