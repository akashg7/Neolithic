/**
 * ChatDrawer — the sheet that rises from the launcher. Full-width bottom
 * sheet on a phone; a right-hand panel on wide web, so desktop reviewers get
 * a console beside the app instead of a phone-shaped box stretched out.
 * Swipe the handle down to dismiss; the transcript is kept for next time.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Easing, KeyboardAvoidingView, Modal, PanResponder, Platform, Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors } from '../../theme/tokens';
import { useAgent } from '../../lib/agentContext';
import { ChatPanel } from './ChatPanel';
import { NATIVE_DRIVER } from './motion';

export function ChatDrawer() {
  const { isOpen, close } = useAgent();
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const wide = width >= 760;
  const sheetH = wide ? height - 32 : Math.round(height * 0.9);

  const [mounted, setMounted] = useState(false);
  const y = useRef(new Animated.Value(sheetH)).current;
  const fade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (isOpen) {
      setMounted(true);
      y.setValue(sheetH);
      Animated.parallel([
        Animated.timing(y, { toValue: 0, duration: 320, easing: Easing.out(Easing.cubic), useNativeDriver: NATIVE_DRIVER }),
        Animated.timing(fade, { toValue: 1, duration: 260, useNativeDriver: NATIVE_DRIVER }),
      ]).start();
    } else if (mounted) {
      Animated.parallel([
        Animated.timing(y, { toValue: sheetH, duration: 240, easing: Easing.in(Easing.cubic), useNativeDriver: NATIVE_DRIVER }),
        Animated.timing(fade, { toValue: 0, duration: 200, useNativeDriver: NATIVE_DRIVER }),
      ]).start(() => setMounted(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const pan = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onPanResponderMove: (_, g) => g.dy > 0 && y.setValue(g.dy),
        onPanResponderRelease: (_, g) => {
          if (g.dy > 90 || g.vy > 0.9) close();
          else Animated.spring(y, { toValue: 0, useNativeDriver: NATIVE_DRIVER, bounciness: 0 }).start();
        },
      }),
    [close, y],
  );

  if (!mounted) return null;

  return (
    <Modal transparent visible animationType="none" onRequestClose={close} statusBarTranslucent>
      <View style={[styles.fill, wide && styles.fillWide]}>
        <Animated.View style={[StyleSheet.absoluteFill, styles.scrim, { opacity: fade }]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={close} accessibilityLabel="close" />
        </Animated.View>

        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={wide ? styles.kavWide : styles.kav} pointerEvents="box-none">
          <Animated.View
            style={[
              styles.sheet,
              wide ? styles.sheetWide : styles.sheetNarrow,
              { height: sheetH, transform: [{ translateY: y }] },
            ]}>
            <View {...pan.panHandlers} style={styles.handleZone} accessibilityElementsHidden>
              <View style={styles.handle} />
            </View>
            <View style={{ flex: 1, paddingBottom: wide ? 0 : insets.bottom }}>
              <ChatPanel onClose={close} />
            </View>
          </Animated.View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, justifyContent: 'flex-end' },
  fillWide: { alignItems: 'flex-end', justifyContent: 'center', padding: 16 },
  scrim: { backgroundColor: 'rgba(28,28,23,0.42)' },
  kav: { width: '100%' },
  kavWide: { width: 440 },
  sheet: {
    backgroundColor: colors.background,
    overflow: 'hidden',
    shadowColor: '#18181B',
    shadowOffset: { width: 0, height: -8 },
    shadowOpacity: 0.22,
    shadowRadius: 28,
    elevation: 12,
  },
  sheetNarrow: { borderTopLeftRadius: 28, borderTopRightRadius: 28 },
  sheetWide: { borderRadius: 24 },
  handleZone: { height: 22, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  handle: { width: 44, height: 5, borderRadius: 3, backgroundColor: colors.borderField },
});
