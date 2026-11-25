/**
 * S28 — assistant, full screen.
 *
 * ★ Was a static 12-question FAQ (canned answers, nothing generative). It is
 *   now the same conversation the floating launcher opens — one transcript,
 *   one implementation (`ChatPanel`) — so a farmer who starts in the drawer
 *   and lands here keeps their thread.
 *
 * ★ The agent answers from deterministic engines and a cited knowledge base,
 *   never from free generation (CLAUDE.md §9). The old FAQ keys are kept in
 *   the dictionaries for the knowledge-base seed content (Member 4).
 */
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors } from '../../theme/tokens';
import { ChatPanel } from '../../components/chat/ChatPanel';

export default function S28_Assistant() {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.root, { paddingBottom: insets.bottom }]}>
      <ChatPanel bare />
    </View>
  );
}

const styles = StyleSheet.create({ root: { flex: 1, backgroundColor: colors.background } });
