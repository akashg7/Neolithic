import { Platform } from 'react-native';
/** react-native-web has no native animation driver; asking for it only logs warnings. */
export const NATIVE_DRIVER = Platform.OS !== 'web';
