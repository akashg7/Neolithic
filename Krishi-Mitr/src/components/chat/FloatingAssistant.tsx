/**
 * FloatingAssistant — the launcher. A stamp-and-word pill, not a bare circle:
 * the word ("विचारा" / "Ask") says what it does to a farmer who has never seen
 * a chat bubble icon. It rings once on first mount to be noticed, then stays
 * still — it never bounces or pulses for attention again.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, fontFamily, radius, weights } from '../../theme/tokens';
import { useT } from '../../lib/i18n';
import { useAgent } from '../../lib/agentContext';
import { NATIVE_DRIVER } from './motion';
import { Seal } from './Seal';

// Screens that already are a chat, or that cover the whole app (menu, language).
const HIDDEN_ON = new Set(['Assistant', 'Menu', 'LanguageSwitcher']);

export function FloatingAssistant() {
  const { t } = useT();
  const { isOpen, open, screen } = useAgent();
  const insets = useSafeAreaInsets();
  const ring = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const id = setTimeout(() => {
      Animated.timing(ring, { toValue: 1, duration: 1400, easing: Easing.out(Easing.quad), useNativeDriver: NATIVE_DRIVER }).start();
    }, 1200);
    return () => clearTimeout(id);
  }, [ring]);

  if (isOpen || HIDDEN_ON.has(screen.current_screen)) return null;

  // Native keeps clear of the 64pt tab bar; on web the navbar sits on top, so the corner is free.
  const bottom = Platform.OS === 'web' ? 24 : 64 + insets.bottom + 16;

  return (
    <View pointerEvents="box-none" style={[styles.anchor, { bottom }]}>
      <Animated.View
        pointerEvents="none"
        style={[
          styles.ring,
          {
            opacity: ring.interpolate({ inputRange: [0, 0.15, 1], outputRange: [0, 0.5, 0] }),
            transform: [{ scale: ring.interpolate({ inputRange: [0, 1], outputRange: [1, 1.6] }) }],
          },
        ]}
      />
      <TouchableOpacity
        onPress={open}
        activeOpacity={0.88}
        style={styles.pill}
        accessibilityRole="button"
        accessibilityLabel={t('chat_title')}>
        <Seal size={44} label={t('chat_fab_seal')} />
        <Text style={styles.word}>{t('chat_fab_label')}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  anchor: { position: 'absolute', right: 16, alignItems: 'flex-end' },
  ring: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    width: '100%',
    height: 52,
    borderRadius: radius.full,
    backgroundColor: colors.primaryContainer,
  },
  pill: {
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingLeft: 4,
    paddingRight: 18,
    borderRadius: radius.full,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.primaryContainer,
    shadowColor: '#C2410C',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.22,
    shadowRadius: 14,
    elevation: 6,
  },
  word: { fontFamily: fontFamily.bold, fontWeight: weights.bold, fontSize: 17, color: colors.primary },
});
