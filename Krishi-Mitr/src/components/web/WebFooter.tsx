/**
 * WebFooter — the footer for the web version of Krishi Mitr.
 *
 * ★ Web-only. Returns null on non-web platforms.
 * ★ Keeps it compact: branding + quick links + copyright.
 */

import React from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { colors, fontFamily, space, radius } from '../../theme/tokens';
import { Logo } from '../ui/Logo';
import { Icon } from '../ui/Icon';
import { useT } from '../../lib/i18n';
import { navigationRef } from '../../navigation/navigationRef';

export function WebFooter() {
  if (Platform.OS !== 'web') return null;

  const { t } = useT();

  const navigateToTab = (tab: string) => {
    if (navigationRef.isReady()) {
      (navigationRef as any).navigate('FarmerTabs', { screen: tab });
    }
  };

  return (
    <View style={styles.footer}>
      <View style={styles.footerInner}>
        {/* ── Brand Column ──────────────────────────────────── */}
        <View style={styles.col}>
          <View style={styles.footerBrand}>
            <Logo size={28} background={colors.inverseSurface} foreground={colors.inverseOnSurface} />
            <Text style={styles.footerBrandText}>{t('app_name')}</Text>
          </View>
          <Text style={styles.footerDesc}>
            खरा बाजारभाव, स्पष्ट सल्ला — शेतकऱ्यांसाठी.
          </Text>
        </View>

        {/* ── Quick Links ───────────────────────────────────── */}
        <View style={styles.col}>
          <Text style={styles.colTitle}>Quick Links</Text>
          {[
            { label: t('tab_home'), tab: 'Home' },
            { label: t('tab_market'), tab: 'Prices' },
            { label: t('tab_my_produce'), tab: 'MyLots' },
            { label: t('tab_deals'), tab: 'Deals' },
          ].map(link => (
            <TouchableOpacity
              key={link.tab}
              onPress={() => navigateToTab(link.tab)}
              activeOpacity={0.7}
              style={styles.footerLink}
            >
              <Text style={styles.footerLinkText}>{link.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Support ───────────────────────────────────────── */}
        <View style={styles.col}>
          <Text style={styles.colTitle}>Support</Text>
          <TouchableOpacity
            onPress={() => {
              if (navigationRef.isReady()) {
                (navigationRef as any).navigate('Assistant');
              }
            }}
            activeOpacity={0.7}
            style={styles.footerLink}
          >
            <Text style={styles.footerLinkText}>{t('tab_assistant')}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => {
              if (navigationRef.isReady()) {
                (navigationRef as any).navigate('LanguageSwitcher');
              }
            }}
            activeOpacity={0.7}
            style={styles.footerLink}
          >
            <Text style={styles.footerLinkText}>{t('select_language')}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ── Bottom Copyright Bar ───────────────────────────── */}
      <View style={styles.copyrightBar}>
        <Text style={styles.copyrightText}>
          © 2026 Krishi Mitr · Made for Indian Farmers
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    backgroundColor: colors.inverseSurface,
    paddingTop: 40,
  },
  footerInner: {
    flexDirection: 'row',
    paddingHorizontal: 40,
    paddingBottom: 32,
    maxWidth: 1440,
    // @ts-ignore
    marginLeft: 'auto',
    // @ts-ignore
    marginRight: 'auto',
    width: '100%',
    gap: 60,
    flexWrap: 'wrap',
  },
  col: {
    minWidth: 160,
    gap: 8,
  },
  footerBrand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 4,
  },
  footerBrandText: {
    fontFamily: fontFamily.extraBold,
    fontSize: 18,
    color: colors.inverseOnSurface,
    letterSpacing: -0.2,
  },
  footerDesc: {
    fontFamily: fontFamily.regular,
    fontSize: 13,
    color: colors.surfaceContainerHighest,
    lineHeight: 20,
    maxWidth: 240,
  },
  colTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: colors.surfaceContainerHighest,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  footerLink: {
    paddingVertical: 3,
    // @ts-ignore
    cursor: 'pointer',
  },
  footerLinkText: {
    fontFamily: fontFamily.medium,
    fontSize: 14,
    color: colors.surfaceDim,
    // @ts-ignore
    transition: 'color 0.15s ease',
  },
  copyrightBar: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.08)',
    paddingVertical: 16,
    paddingHorizontal: 40,
    alignItems: 'center',
  },
  copyrightText: {
    fontFamily: fontFamily.regular,
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',
    letterSpacing: 0.3,
  },
});
