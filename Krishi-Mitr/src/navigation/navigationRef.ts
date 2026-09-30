/**
 * Module-level navigation ref — lets components outside the navigator tree
 * (like the web navbar) navigate and read state without being a screen.
 *
 * ★ This is the official React Navigation pattern for "navigating without the
 *   navigation prop." `App.tsx` passes this ref to `NavigationContainer`, and
 *   any module that imports it can `navigationRef.navigate(...)` after the
 *   container mounts.
 */
import { createNavigationContainerRef } from '@react-navigation/native';

export const navigationRef = createNavigationContainerRef<Record<string, object | undefined>>();
