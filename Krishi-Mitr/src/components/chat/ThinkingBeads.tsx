/**
 * ThinkingBeads — the waiting state, drawn as a counting frame. Five beads
 * slide along a wire and settle, the way a trader tallies. It says "working
 * it out" without a spinner or a typing-dots cliché, and it is honest: the
 * backend returns whole answers, so nothing here pretends to stream text.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import { colors, type as typography } from '../../theme/tokens';
import { useT } from '../../lib/i18n';
import { NATIVE_DRIVER } from './motion';

const BEADS = 5;
const TRAVEL = 74;

export function ThinkingBeads() {
  const { t } = useT();
  const slide = useRef(Array.from({ length: BEADS }, () => new Animated.Value(0))).current;

  useEffect(() => {
    const loops = slide.map((v, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 90),
          Animated.timing(v, { toValue: 1, duration: 520, easing: Easing.inOut(Easing.cubic), useNativeDriver: NATIVE_DRIVER }),
          Animated.delay((BEADS - i) * 90 + 220),
          Animated.timing(v, { toValue: 0, duration: 520, easing: Easing.inOut(Easing.cubic), useNativeDriver: NATIVE_DRIVER }),
          Animated.delay(i * 40),
        ]),
      ),
    );
    loops.forEach(l => l.start());
    return () => loops.forEach(l => l.stop());
  }, [slide]);

  return (
    <View style={styles.row} accessibilityRole="progressbar" accessibilityLabel={t('chat_thinking')}>
      <View style={styles.frame}>
        <View style={styles.wire} />
        {slide.map((v, i) => (
          <Animated.View
            key={i}
            style={[
              styles.bead,
              { left: i * 14, transform: [{ translateX: v.interpolate({ inputRange: [0, 1], outputRange: [0, TRAVEL - i * 14 - 8] }) }] },
            ]}
          />
        ))}
        <View style={[styles.post, { left: 0 }]} />
        <View style={[styles.post, { right: 0 }]} />
      </View>
      <Text style={styles.label}>{t('chat_thinking')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 6 },
  frame: { width: 86, height: 22, justifyContent: 'center' },
  wire: { position: 'absolute', left: 0, right: 0, top: 10, height: 2, backgroundColor: colors.borderField, borderRadius: 1 },
  bead: {
    position: 'absolute',
    top: 3,
    width: 14,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.primaryContainer,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  post: { position: 'absolute', top: 0, width: 2, height: 22, backgroundColor: colors.outline, borderRadius: 1 },
  label: { ...typography.bodySm, color: colors.onSurfaceVariant },
});
