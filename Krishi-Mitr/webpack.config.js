/**
 * The web build of Krishi Mitr.
 *
 * The screens in `src/` are the *same files* that run on the phone — this is a
 * React Native codebase compiled for the browser through `react-native-web`,
 * not a rewrite. That is deliberate: a second implementation of 45 screens
 * would drift from the app within a week, and the demo would then have two
 * different products wearing one name.
 *
 * Two things make that work:
 *
 *   1. `react-native$ → react-native-web`, so `View`/`Text`/`StyleSheet`
 *      resolve to their DOM implementations.
 *   2. The five native modules below have no browser equivalent, so each one
 *      is aliased to a shim in `src/web-shims/` that implements the same API
 *      on a web platform feature (Web Speech, MediaRecorder, a file input).
 */

const path = require('path');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const appDirectory = path.resolve(__dirname);

const babelLoaderConfiguration = {
  test: /\.(tsx|ts|jsx|js)$/,
  include: [
    path.resolve(appDirectory, 'index.web.js'),
    path.resolve(appDirectory, 'App.tsx'),
    path.resolve(appDirectory, 'src'),
  ],
  use: {
    loader: 'babel-loader',
    options: {
      cacheDirectory: true,
      presets: [
        ['@babel/preset-env', { targets: { browsers: ['>0.5%', 'not dead'] } }],
        ['@babel/preset-react', { runtime: 'automatic' }],
        '@babel/preset-typescript',
      ],
      // ★ No `react-native-web` babel plugin here, deliberately. It rewrites
      //   every `from 'react-native'` to a deep path inside react-native-web,
      //   which is a bundle-size win and which also routes straight past the
      //   `react-native$` alias below — and that alias is what supplies
      //   `PermissionsAndroid`. Resolution has to go through one door for the
      //   shim to mean anything.
      plugins: [],
    },
  },
};

module.exports = {
  mode: process.env.NODE_ENV || 'development',
  entry: [path.resolve(appDirectory, 'index.web.js')],
  output: {
    filename: 'bundle.[contenthash].js',
    path: path.resolve(appDirectory, 'dist'),
    publicPath: '/',
    clean: true,
  },
  module: {
    rules: [
      { test: /\.m?js$/, resolve: { fullySpecified: false } },
      babelLoaderConfiguration,
      { test: /\.(gif|jpe?g|png|svg|mp3|wav)$/, type: 'asset/resource' },
    ],
  },
  resolve: {
    alias: {
      // Everything react-native-web exports, plus PermissionsAndroid, which it
      // does not — see the shim's header for why that one absence blanked the
      // entire page.
      'react-native$': path.resolve(appDirectory, 'src/web-shims/react-native.ts'),

      // The native modules. Each shim exports the same surface the screens
      // already call, backed by a browser API — see src/web-shims/README.md.
      'react-native-sound': path.resolve(appDirectory, 'src/web-shims/sound.ts'),
      'react-native-tts': path.resolve(appDirectory, 'src/web-shims/tts.ts'),
      'react-native-fs': path.resolve(appDirectory, 'src/web-shims/fs.ts'),
      'react-native-image-picker': path.resolve(appDirectory, 'src/web-shims/image-picker.ts'),
      'react-native-audio-recorder-player': path.resolve(
        appDirectory,
        'src/web-shims/audio-recorder-player.ts',
      ),

      // Pulled in by react-native-svg's web build, and shipped as Flow source
      // that webpack cannot parse. Nothing here puts a bundled image inside an
      // SVG, so a stub is honest — see the shim's own header.
      '@react-native/assets-registry/registry': path.resolve(
        appDirectory,
        'src/web-shims/assets-registry.ts',
      ),
    },
    extensions: [
      '.web.tsx',
      '.web.ts',
      '.web.jsx',
      '.web.js',
      '.tsx',
      '.ts',
      '.jsx',
      '.js',
      '.json',
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: path.resolve(appDirectory, 'public/index.html'),
      filename: 'index.html',
      chunks: ['main'],
    }),
    new HtmlWebpackPlugin({
      template: path.resolve(appDirectory, 'public/video.html'),
      filename: 'video.html',
      inject: false,
    }),
    new webpack.DefinePlugin({
      __DEV__: JSON.stringify(process.env.NODE_ENV !== 'production'),
      'process.env': JSON.stringify({
        NODE_ENV: process.env.NODE_ENV || 'development',
        SARVAM_API_KEY: (() => {
          let k = process.env.SARVAM_API_KEY || '';
          if (!k) {
            try {
              const fs = require('fs');
              const envPath = path.resolve(appDirectory, '.env');
              if (fs.existsSync(envPath)) {
                const lines = fs.readFileSync(envPath, 'utf8').split('\n');
                for (const line of lines) {
                  const match = line.match(/^SARVAM_API_KEY\s*=\s*(.+)$/);
                  if (match) {
                    k = match[1].trim();
                    break;
                  }
                }
              }
            } catch {}
          }
          return k;
        })(),
      }),
    }),
    {
      apply: (compiler) => {
        compiler.hooks.afterEmit.tap('AutoCopyStaticPlugin', () => {
          const fs = require('fs');
          const fromDir = path.resolve(appDirectory, 'public');
          const toDir = path.resolve(appDirectory, 'dist');
          if (!fs.existsSync(fromDir)) return;
          function copyRec(src, dest) {
            if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
            for (const item of fs.readdirSync(src)) {
              if (item === 'index.html' && src === fromDir) continue;
              const sPath = path.join(src, item);
              const dPath = path.join(dest, item);
              if (fs.statSync(sPath).isDirectory()) copyRec(sPath, dPath);
              else fs.copyFileSync(sPath, dPath);
            }
          }
          try {
            copyRec(fromDir, toDir);
          } catch (e) {
            console.error('AutoCopyStaticPlugin error:', e);
          }
        });
      },
    },
  ],
  performance: { hints: false },
  devServer: {
    host: '0.0.0.0',
    port: 8080,
    static: {
      directory: path.resolve(appDirectory, 'public'),
      publicPath: '/',
    },
    historyApiFallback: {
      rewrites: [
        { from: /^\/video$/, to: '/video.html' },
      ],
    },
    hot: true,
    allowedHosts: 'all',
    client: {
      overlay: {
        errors: true,
        warnings: false,
      },
    },
  },
};
