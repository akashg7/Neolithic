/**
 * LedgerPaper — the conversation's page. Faint ruled lines and a double
 * margin rule in marigold, like a bahi-khata. Static behind the scroll, so it
 * costs one SVG, not one view per line.
 */
import React, { useState } from 'react';
import { LayoutChangeEvent, StyleSheet, View } from 'react-native';
import Svg, { Line } from 'react-native-svg';
import { colors } from '../../theme/tokens';
import { MARGIN } from './MessageRow';

const STEP = 34;

export function LedgerPaper() {
  const [size, setSize] = useState({ w: 0, h: 0 });
  const rows = Math.ceil(size.h / STEP);
  return (
    <View
      pointerEvents="none"
      style={StyleSheet.absoluteFill}
      onLayout={(e: LayoutChangeEvent) => setSize({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
      {size.w > 0 ? (
        <Svg width={size.w} height={size.h}>
          {Array.from({ length: rows }, (_, i) => (
            <Line key={i} x1={0} x2={size.w} y1={(i + 1) * STEP} y2={(i + 1) * STEP} stroke={colors.borderCard} strokeWidth={1} opacity={0.55} />
          ))}
          <Line x1={MARGIN - 5} x2={MARGIN - 5} y1={0} y2={size.h} stroke={colors.primaryContainer} strokeWidth={1} opacity={0.28} />
          <Line x1={MARGIN - 2} x2={MARGIN - 2} y1={0} y2={size.h} stroke={colors.primaryContainer} strokeWidth={1} opacity={0.28} />
        </Svg>
      ) : null}
    </View>
  );
}
