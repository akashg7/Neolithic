/**
 * WebNavbar — the top navigation bar for the web version of Krishi Mitr.
 *
 * ★ Replaces the mobile bottom tab bar on web with a standard horizontal
 *   navbar: logo on the left, five navigation tabs in the center, and
 *   language/profile controls on the right.
 *
 * ★ Uses URL-based active tab detection via `history.pushState` interception,
 *   and navigates via the module-level `navigationRef` — so it works from
 *   outside the navigator tree.
 *
 * ★ Web-only component. Returns null on non-web platforms.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { colors, fontFamily, space, radius } from '../../theme/tokens';
import { Icon } from '../ui/Icon';
import { Logo } from '../ui/Logo';
import { useAuth } from '../../lib/auth';
import { useT } from '../../lib/i18n';
import { navigationRef } from '../../navigation/navigationRef';
import type { IconName } from '../ui/Icon';
import type { Locale } from '../../types/api';

/** Tab configuration matching the webLinking URL paths. */
const TAB_CONFIG: { name: string; icon: IconName; pathPrefix: string }[] = [
  { name: 'Home', icon: 'home', pathPrefix: '/app/home' },
  { name: 'Prices', icon: 'chart-bar', pathPrefix: '/app/prices' },
  { name: 'MyLots', icon: 'box', pathPrefix: '/app/lots' },
  { name: 'Talks', icon: 'message-circle', pathPrefix: '/app/talks' },
  { name: 'Deals', icon: 'handshake', pathPrefix: '/app/deals' },
];

const LANGUAGES: { code: Locale; label: string }[] = [
  { code: 'mr', label: 'मराठी' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'en', label: 'English' },
];

/** Derive the active tab from the current URL pathname. */
function getActiveTabFromPath(): string {
  if (typeof window === 'undefined') return 'Home';
  const path = window.location.pathname;
  for (const tab of TAB_CONFIG) {
    if (path.startsWith(tab.pathPrefix)) return tab.name;
  }
  // Default to Home for root or unmatched paths
  if (path === '/' || path.startsWith('/app')) return 'Home';
  return '';
}

export function WebNavbar() {
  // ★ Web-only guard
  if (Platform.OS !== 'web') return null;

  const { user, signOut } = useAuth();
  const { t, locale, setLocale } = useT();
  const [activeTab, setActiveTab] = useState(getActiveTabFromPath);
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  // ── Track navigation changes via URL ────────────────────────────────
  useEffect(() => {
    const update = () => setActiveTab(getActiveTabFromPath());

    // Intercept history mutations so we catch programmatic navigations
    const origPush = history.pushState.bind(history);
    const origReplace = history.replaceState.bind(history);

    history.pushState = function (...args: Parameters<typeof origPush>) {
      origPush(...args);
      requestAnimationFrame(update);
    };
    history.replaceState = function (...args: Parameters<typeof origReplace>) {
      origReplace(...args);
      requestAnimationFrame(update);
    };

    window.addEventListener('popstate', update);

    return () => {
      history.pushState = origPush;
      history.replaceState = origReplace;
      window.removeEventListener('popstate', update);
    };
  }, []);

  // Close profile dropdown when clicking outside
  useEffect(() => {
    if (!showProfileMenu) return;
    const close = () => setShowProfileMenu(false);
    // Delay so the current click doesn't immediately close it
    const timer = setTimeout(() => {
      document.addEventListener('click', close, { once: true });
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', close);
    };
  }, [showProfileMenu]);

  // ── Navigation ──────────────────────────────────────────────────────
  const navigateToTab = useCallback((tabName: string) => {
    if (navigationRef.isReady()) {
      (navigationRef as any).navigate('FarmerTabs', { screen: tabName });
    }
    setActiveTab(tabName);
  }, []);

  const tabLabels: Record<string, string> = {
    Home: t('tab_home'),
    Prices: t('tab_market'),
    MyLots: t('tab_my_produce'),
    Talks: t('tab_chat'),
    Deals: t('tab_deals'),
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <View style={styles.navbar}>
      <View style={styles.navInner}>
        {/* ── Left: Logo + Brand ─────────────────────────────────── */}
        <TouchableOpacity
          style={styles.brand}
          onPress={() => navigateToTab('Home')}
          activeOpacity={0.8}
        >
          <Logo size={36} />
          <Text style={styles.brandText}>{t('app_name')}</Text>
        </TouchableOpacity>

        {/* ── Center: Navigation Tabs ────────────────────────────── */}
        <View style={styles.tabs}>
          {TAB_CONFIG.map(tab => {
            const isActive = activeTab === tab.name;
            return (
              <TouchableOpacity
                key={tab.name}
                style={[styles.tab, isActive && styles.tabActive]}
                onPress={() => navigateToTab(tab.name)}
                activeOpacity={0.7}
                accessibilityRole="link"
                accessibilityLabel={tabLabels[tab.name] || tab.name}
              >
                <Icon
                  name={tab.icon}
                  size={19}
                  color={isActive ? colors.primaryContainer : colors.outline}
                />
                <Text
                  style={[styles.tabText, isActive && styles.tabTextActive]}
                  numberOfLines={1}
                >
                  {tabLabels[tab.name] || tab.name}
                </Text>
                {isActive && <View style={styles.tabIndicator} />}
              </TouchableOpacity>
            );
          })}
        </View>

        {/* ── Right: Language + Profile ──────────────────────────── */}
        <View style={styles.rightSection}>
          {/* Language pills */}
          <View style={styles.langRow}>
            {LANGUAGES.map(lang => (
              <TouchableOpacity
                key={lang.code}
                style={[
                  styles.langPill,
                  locale === lang.code && styles.langPillActive,
                ]}
                onPress={() => setLocale(lang.code)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.langText,
                    locale === lang.code && styles.langTextActive,
                  ]}
                >
                  {lang.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Video Walkthrough link */}
          <TouchableOpacity
            style={styles.videoNavBtn}
            onPress={() => {
              if (typeof window !== 'undefined') window.open('/video', '_blank');
            }}
            // @ts-ignore
            onClick={() => {
              if (typeof window !== 'undefined') window.open('/video', '_blank');
            }}
            activeOpacity={0.7}
            accessibilityRole="link"
            accessibilityLabel="Watch Demo Video"
          >
            <Icon name="video" size={14} color={colors.primary} />
            <Text style={styles.videoNavText}>
              {locale === 'mr' ? 'व्हिडिओ' : locale === 'hi' ? 'वीडियो' : 'Video'}
            </Text>
          </TouchableOpacity>

          {/* Divider */}
          <View style={styles.vertDivider} />

          {/* Profile button */}
          <TouchableOpacity
            style={styles.profileBtn}
            onPress={() => setShowProfileMenu(prev => !prev)}
            activeOpacity={0.7}
          >
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(user?.name?.trim()?.[0] ?? '?').toUpperCase()}
              </Text>
            </View>
            <Text style={styles.profileName} numberOfLines={1}>
              {user?.name ?? ''}
            </Text>
            <Icon name="chevron-down" size={14} color={colors.outline} />
          </TouchableOpacity>

          {/* Profile dropdown */}
          {showProfileMenu && (
            <View style={styles.dropdown}>
              {/* Farmer profile */}
              <TouchableOpacity
                style={styles.dropdownItem}
                onPress={() => {
                  setShowProfileMenu(false);
                  if (navigationRef.isReady()) {
                    (navigationRef as any).navigate('FarmerTabs', {
                      screen: 'MyLots',
                      params: { screen: 'S35_FarmerProfile' },
                    });
                  }
                }}
              >
                <View style={styles.dropdownIconBg}>
                  <Icon name="edit" size={15} color={colors.primary} />
                </View>
                <Text style={styles.dropdownText}>{t('profile_title')}</Text>
              </TouchableOpacity>

              {/* Language settings */}
              <TouchableOpacity
                style={styles.dropdownItem}
                onPress={() => {
                  setShowProfileMenu(false);
                  if (navigationRef.isReady()) {
                    (navigationRef as any).navigate('LanguageSwitcher');
                  }
                }}
              >
                <View style={styles.dropdownIconBg}>
                  <Icon name="globe" size={15} color={colors.primary} />
                </View>
                <Text style={styles.dropdownText}>{t('select_language')}</Text>
              </TouchableOpacity>

              {/* AI Assistant */}
              <TouchableOpacity
                style={styles.dropdownItem}
                onPress={() => {
                  setShowProfileMenu(false);
                  if (navigationRef.isReady()) {
                    (navigationRef as any).navigate('Assistant');
                  }
                }}
              >
                <View style={styles.dropdownIconBg}>
                  <Icon name="message-circle" size={15} color={colors.tertiary} />
                </View>
                <Text style={styles.dropdownText}>{t('tab_assistant')}</Text>
              </TouchableOpacity>

              <View style={styles.dropdownDivider} />

              {/* Sign out */}
              <TouchableOpacity
                style={styles.dropdownItem}
                onPress={() => {
                  setShowProfileMenu(false);
                  signOut();
                }}
              >
                <View style={[styles.dropdownIconBg, { backgroundColor: 'rgba(220,38,38,0.08)' }]}>
                  <Icon name="x-circle" size={15} color={colors.critical} />
                </View>
                <Text style={[styles.dropdownText, { color: colors.critical }]}>
                  {t('root_sign_out')}
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────
const NAVBAR_HEIGHT = 64;

const styles = StyleSheet.create({
  navbar: {
    height: NAVBAR_HEIGHT,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderCard,
    // @ts-ignore — web-only property
    position: 'sticky',
    top: 0,
    // @ts-ignore — web-only
    zIndex: 1000,
    shadowColor: '#18181B',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  navInner: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 28,
    maxWidth: 1440,
    width: '100%',
    alignSelf: 'center',
  },

  // ── Brand ────────────────────────────────────────────────
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginRight: 32,
    // @ts-ignore
    cursor: 'pointer',
  },
  brandText: {
    fontFamily: fontFamily.extraBold,
    fontSize: 20,
    color: colors.primary,
    letterSpacing: -0.3,
  },

  // ── Tabs ─────────────────────────────────────────────────
  tabs: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: radius.md,
    // @ts-ignore
    cursor: 'pointer',
    // @ts-ignore — web-only for smooth hover
    transition: 'background-color 0.15s ease, transform 0.1s ease',
  },
  tabActive: {
    backgroundColor: 'rgba(194, 65, 12, 0.07)',
  },
  tabText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 14,
    color: colors.outline,
    letterSpacing: 0.1,
    // @ts-ignore
    transition: 'color 0.15s ease',
    // @ts-ignore — no text selection on nav items
    userSelect: 'none',
  },
  tabTextActive: {
    color: colors.primaryContainer,
    fontFamily: fontFamily.bold,
  },
  tabIndicator: {
    position: 'absolute',
    bottom: -1,
    left: 12,
    right: 12,
    height: 2.5,
    borderRadius: 2,
    backgroundColor: colors.primaryContainer,
  },

  // ── Right section ────────────────────────────────────────
  rightSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    // @ts-ignore — for dropdown positioning
    position: 'relative',
  },
  langRow: {
    flexDirection: 'row',
    gap: 3,
  },
  langPill: {
    paddingHorizontal: 11,
    paddingVertical: 5,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: 'transparent',
    backgroundColor: 'transparent',
    // @ts-ignore
    cursor: 'pointer',
    // @ts-ignore
    transition: 'all 0.15s ease',
  },
  langPillActive: {
    backgroundColor: colors.primaryContainer,
    borderColor: colors.primaryContainer,
  },
  langText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 12.5,
    color: colors.outline,
    letterSpacing: 0.1,
    // @ts-ignore
    userSelect: 'none',
  },
  langTextActive: {
    color: colors.onPrimary,
    fontFamily: fontFamily.bold,
  },

  videoNavBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 11,
    paddingVertical: 5,
    borderRadius: radius.full,
    backgroundColor: '#FFF7ED',
    borderWidth: 1.2,
    borderColor: '#FDBA74',
    // @ts-ignore
    cursor: 'pointer',
    // @ts-ignore
    transition: 'all 0.15s ease',
  },
  videoNavText: {
    fontFamily: fontFamily.bold,
    fontSize: 12.5,
    color: colors.primary,
    // @ts-ignore
    userSelect: 'none',
  },

  vertDivider: {
    width: 1,
    height: 28,
    backgroundColor: colors.outlineVariant,
    marginHorizontal: 4,
  },

  profileBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: radius.md,
    // @ts-ignore
    cursor: 'pointer',
    // @ts-ignore
    transition: 'background-color 0.15s ease',
  },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: colors.surfaceContainer,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: colors.outlineVariant,
  },
  avatarText: {
    fontFamily: fontFamily.extraBold,
    fontSize: 14,
    color: colors.primary,
  },
  profileName: {
    fontFamily: fontFamily.semiBold,
    fontSize: 13,
    color: colors.onSurface,
    maxWidth: 120,
  },

  // ── Dropdown ─────────────────────────────────────────────
  dropdown: {
    position: 'absolute',
    top: 48,
    right: 0,
    minWidth: 220,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderCard,
    shadowColor: '#18181B',
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.12,
    shadowRadius: 24,
    elevation: 8,
    paddingVertical: 6,
    // @ts-ignore
    zIndex: 2000,
  },
  dropdownItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
    // @ts-ignore
    cursor: 'pointer',
    // @ts-ignore
    transition: 'background-color 0.12s ease',
  },
  dropdownIconBg: {
    width: 30,
    height: 30,
    borderRadius: 8,
    backgroundColor: 'rgba(155,47,0,0.07)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dropdownText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 14,
    color: colors.onSurface,
  },
  dropdownDivider: {
    height: 1,
    backgroundColor: colors.outlineVariant,
    marginVertical: 4,
    marginHorizontal: 12,
  },
});

export { NAVBAR_HEIGHT };
