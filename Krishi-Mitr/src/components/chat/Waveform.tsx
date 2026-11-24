/**
 * Waveform — live bars while the mic is open. Driven by a sine per bar, not
 * by real input level (the recorder library exposes none on web), so it
 * signals "I am listening", never "I hear you at X dB".
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import { colors } from '../../theme/tokens';
import { NATIVE_DRIVER } from './motion';

const BARS = 22;

export function Waveform({ active }: { active: boolean }) {
  const bars = useRef(Array.from({ length: BARS }, () => new Animated.Value(0.2))).current;

  useEffect(() => {
    if (!active) {
      bars.forEach(b => b.setValue(0.2));
      return;
    }
    const loops = bars.map((b, i) => {
      const peak = 0.45 + 0.55 * Math.abs(Math.sin(i * 1.7));
      return Animated.loop(
        Animated.sequence([
          Animated.timing(b, { toValue: peak, duration: 260 + (i % 5) * 70, easing: Easing.inOut(Easing.quad), useNativeDriver: NATIVE_DRIVER }),
          Animated.timing(b, { toValue: 0.15, duration: 300 + (i % 4) * 60, easing: Easing.inOut(Easing.quad), useNativeDriver: NATIVE_DRIVER }),
        ]),
      );
    });
    loops.forEach(l => l.start());
    return () => loops.forEach(l => l.stop());
  }, [active, bars]);

  return (
    <View style={styles.row}>
      {bars.map((b, i) => (
        <Animated.View key={i} style={[styles.bar, { transform: [{ scaleY: b }] }]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 3, height: 32 },
  bar: { width: 3, height: 32, borderRadius: 2, backgroundColor: colors.primaryContainer },
});
