/**
 * Seal — the assistant's mark. A trader's rubber stamp: solid marigold disc,
 * a dashed inner ring, the glyph struck in the middle. Used as the launcher,
 * the avatar beside each reply, and the header mark, so the assistant has
 * exactly one face.
 */
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fontFamily, weights } from '../../theme/tokens';

export function Seal({ size = 36, label, ring = true }: { size?: number; label: string; ring?: boolean }) {
  const inset = Math.max(3, Math.round(size * 0.1));
  return (
    <View style={[styles.disc, { width: size, height: size, borderRadius: size / 2 }]}>
      {ring ? (
        <View
          style={[
            styles.ring,
            { top: inset, left: inset, right: inset, bottom: inset, borderRadius: size / 2 },
          ]}
        />
      ) : null}
      <Text style={[styles.glyph, { fontSize: Math.round(size * 0.36) }]} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  disc: { backgroundColor: colors.primaryContainer, alignItems: 'center', justifyContent: 'center' },
  ring: {
    position: 'absolute',
    borderWidth: 1.25,
    borderStyle: 'dashed',
    borderColor: 'rgba(255,236,231,0.75)',
  },
  glyph: {
    color: colors.onPrimaryContainer,
    fontFamily: fontFamily.extraBold,
    fontWeight: weights.extraBold,
    includeFontPadding: false,
  },
});
