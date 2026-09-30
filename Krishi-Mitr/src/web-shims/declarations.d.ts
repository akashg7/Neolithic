declare module 'react-native-web';
declare module 'react-native-sound' {
  export default class Sound {
    static setCategory(category: string): void;
    static MAIN_BUNDLE: string;
    constructor(path: string, basePath: string, callback?: (error?: any) => void);
    play(callback?: (success: boolean) => void): void;
    stop(callback?: () => void): void;
    release(): void;
  }
}
declare module 'react-native-tts' {
  const Tts: any;
  export default Tts;
}
declare module 'react-native-audio-recorder-player' {
  export const AudioEncoderAndroidType: any;
  export const AudioSourceAndroidType: any;
  export const OutputFormatAndroidType: any;
  const AudioRecorderPlayer: any;
  export default AudioRecorderPlayer;
}
declare module 'react-native-image-picker' {
  export function launchCamera(options: any, callback: (response: any) => void): void;
  export function launchImageLibrary(options: any, callback: (response: any) => void): void;
}
