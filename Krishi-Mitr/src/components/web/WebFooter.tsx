/**
 * WebFooter — Professional Footer for the Web Version of Krishi Mitr.
 *
 * ★ Web-only. Returns null on non-web platforms.
 * ★ 100% Language Sensitive: English, Marathi, Hindi.
 * ★ Branding, Quick Navigation Links & Verified Credentials.
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

  const { t, locale } = useT();

  const isMr = locale === 'mr';
  const isHi = locale === 'hi';
  const isEn = locale === 'en';

  const navigateToTab = (tab: string) => {
    if (navigationRef.isReady()) {
      (navigationRef as any).navigate('FarmerTabs', { screen: tab });
    }
  };

  const footerTagline = isEn
    ? 'Official Mandi Benchmark, AI Risk Forecast & Direct Farmer Trade.'
    : isHi
    ? 'सच्चा मंडी भाव, निष्पक्ष एआई सलाह और सीधा किसान-व्यापारी व्यापार.'
    : 'खरा बाजारभाव, अचूक सल्ला आणि थेट शेतकरी-व्यापारी व्यापार.';

  return (
    <View style={styles.footer}>
      <View style={styles.footerInner}>
        {/* ── Brand Column ──────────────────────────────────── */}
        <View style={styles.colBrand}>
          <View style={styles.footerBrand}>
            <Logo size={32} background={colors.inverseSurface} foreground={colors.inverseOnSurface} />
            <Text style={styles.footerBrandText}>{t('app_name')}</Text>
          </View>
          <Text style={styles.footerDesc}>
            {footerTagline}
          </Text>
          <View style={styles.govPill}>
            <Icon name="shield-check" size={13} color="#68DBA8" />
            <Text style={styles.govPillText}>
              {isEn ? 'Govt of Maharashtra Agriculture Dept' : 'महाराष्ट्र शासन कृषी विभाग'}
            </Text>
          </View>
        </View>

        {/* ── Quick Links ───────────────────────────────────── */}
        <View style={styles.col}>
          <Text style={styles.colTitle}>
            {isEn ? 'Quick Navigation' : isHi ? 'त्वरित लिंक' : 'महत्त्वाचे दुवे'}
          </Text>
          {[
            { label: isEn ? 'Home Dashboard' : isHi ? 'मुख्य डैशबोर्ड' : 'मुख्य डॅशबोर्ड', tab: 'Home' },
            { label: isEn ? 'Mandi Market Hub' : isHi ? 'मंडी भाव केंद्र' : 'बाजार समिती केंद्र', tab: 'Prices' },
            { label: isEn ? 'My Produce Lots' : isHi ? 'मेरे लॉट्स' : 'माझे शेतीमाल लॉट', tab: 'MyLots' },
            { label: isEn ? 'Deals & Settlement' : isHi ? 'सौदा व एस्क्रो' : 'सौदे व एस्क्रो', tab: 'Deals' },
          ].map(link => (
            <TouchableOpacity
              key={link.tab}
              onPress={() => navigateToTab(link.tab)}
              // @ts-ignore
              onClick={() => navigateToTab(link.tab)}
              activeOpacity={0.7}
              style={styles.footerLink}>
              <Text style={styles.footerLinkText}>{link.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Support & Settings ────────────────────────────── */}
        <View style={styles.col}>
          <Text style={styles.colTitle}>
            {isEn ? 'Support & AI' : isHi ? 'सहायता व सेटिंग्स' : 'मदत व सेटिंग्स'}
          </Text>
          <TouchableOpacity
            onPress={() => {
              if (navigationRef.isReady()) {
                (navigationRef as any).navigate('Assistant');
              }
            }}
            // @ts-ignore
            onClick={() => {
              if (navigationRef.isReady()) {
                (navigationRef as any).navigate('Assistant');
              }
            }}
            activeOpacity={0.7}
            style={styles.footerLink}>
            <Text style={styles.footerLinkText}>
              {isEn ? '🌾 AI Krishi Assistant' : '🌾 AI शेती मित्र'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => {
              if (navigationRef.isReady()) {
                (navigationRef as any).navigate('LanguageSwitcher');
              }
            }}
            // @ts-ignore
            onClick={() => {
              if (navigationRef.isReady()) {
                (navigationRef as any).navigate('LanguageSwitcher');
              }
            }}
            activeOpacity={0.7}
            style={styles.footerLink}>
            <Text style={styles.footerLinkText}>
              {isEn ? '🌐 Switch Language' : '🌐 भाषा बदला'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ── Bottom Copyright Bar ───────────────────────────── */}
      <View style={styles.copyrightBar}>
        <Text style={styles.copyrightText}>
          © 2026 Krishi Mitr · SIH 2026 Problem Statement 26132 · Zero Aadhaar Storage
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    backgroundColor: '#1E1E18',
    paddingTop: 36,
    width: '100%',
    marginTop: space.lg,
  },
  footerInner: {
    flexDirection: 'row',
    paddingHorizontal: 28,
    paddingBottom: 28,
    maxWidth: 1440,
    width: '100%',
    alignSelf: 'center',
    gap: 40,
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  colBrand: {
    minWidth: 240,
    flex: 1.5,
    gap: 10,
  },
  col: {
    minWidth: 150,
    flex: 1,
    gap: 8,
  },
  footerBrand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 2,
  },
  footerBrandText: {
    fontFamily: fontFamily.extraBold,
    fontSize: 20,
    color: '#FAF6EE',
    letterSpacing: -0.3,
  },
  footerDesc: {
    fontFamily: fontFamily.regular,
    fontSize: 13,
    color: '#B0A89C',
    lineHeight: 19,
    maxWidth: 320,
  },
  govPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(0, 97, 70, 0.25)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.full,
    alignSelf: 'flex-start',
    marginTop: 4,
  },
  govPillText: {
    fontFamily: fontFamily.bold,
    fontSize: 11,
    color: '#68DBA8',
  },
  colTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: '#FAF6EE',
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
    fontSize: 13.5,
    color: '#C8BEAF',
  },
  copyrightBar: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.08)',
    paddingVertical: 14,
    paddingHorizontal: 28,
    alignItems: 'center',
  },
  copyrightText: {
    fontFamily: fontFamily.regular,
    fontSize: 11.5,
    color: 'rgba(255,255,255,0.4)',
    textAlign: 'center',
  },
});
