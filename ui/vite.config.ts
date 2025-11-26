/// <reference types="vitest" />
import react from '@vitejs/plugin-react-swc';
import { defineConfig, loadEnv } from 'vite';
import eslint from 'vite-plugin-eslint';
import tsconfigPaths from 'vite-tsconfig-paths';
import { configDefaults } from 'vitest/config';

// https://vitejs.dev/config/
const config = ({ mode }) => {
  process.env = { ...process.env, ...loadEnv(mode, process.cwd()) };

  const useMinify = !process.env.npm_package_version?.includes('dev');

  const _eslint = [];

  if (process.env.npm_lifecycle_event !== 'test') {
    _eslint.push({
      // default settings on build (i.e. fail on error)
      ...eslint(),
      apply: 'build'
    });

    _eslint.push({
      // do not fail on serve (i.e. local development)
      ...eslint({
        failOnWarning: false,
        failOnError: false,
        cache: true
      }),
      apply: 'serve',
      enforce: 'post'
    });
  }

  return defineConfig({
    plugins: [
      ..._eslint,
      react(),
      tsconfigPaths(),
      {
        name: 'markdown-loader',
        transform(code, id) {
          if (id.slice(-3) === '.md') {
            // For .md files, get the raw content
            return `export default ${JSON.stringify(code)};`;
          }
        }
      }
    ],
    build: {
      sourcemap: false,
      minify: useMinify
    },
    define: {
      'process.env': {}
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: process.env['VITE_API_TARGET'] ?? 'http://localhost:5000',
          changeOrigin: true
        }
      }
    },
    preview: {
      port: 3000,
      proxy: {
        '/api': {
          target: process.env['VITE_API_TARGET'] ?? 'http://localhost:5000',
          changeOrigin: true
        }
      }
    },
    test: {
      globals: true,
      environment: 'jsdom',
      environmentOptions: {
        jsdom: {
          resources: 'usable'
        }
      },
      setupFiles: ['./src/setupTests.ts'],
      exclude: [...configDefaults.exclude, 'dist/**', 'src/commons/**'],
      testTimeout: 30000,
      reporters: ['junit', 'json', 'default'],
      outputFile: {
        junit: './target/junit-report.xml',
        json: './target/json-report.json'
      },
      coverage: {
        enabled: true,
        provider: 'v8',
        reporter: ['json-summary', 'json', 'html'],
        reportsDirectory: './target/coverage',
        exclude: [
          'vite*config.ts',
          '**/dist/**',
          '**/*.js.map',
          '**/node_modules/**',
          '**/**.test.*',
          '**/**.test.*',
          '**/**.d.ts',
          'src/commons/**',
          'src/tests'
        ],
        reportOnFailure: true
      },
      sequence: { hooks: 'list' },
      pool: 'threads',
      poolOptions: {
        threads: {
          maxThreads: 8,
          minThreads: 6
        }
      },
      onConsoleLog(log, type) {
        const equalityLogs = ['Outstanding requests: 0'];

        const startsWithLogs = [
          'Form is not valid',
          'Executing types',
          'example',
          '[classificationParser]',
          'react-i18next'
        ];

        if (equalityLogs.some(item => log === item)) {
          return false;
        }

        if (startsWithLogs.some(item => log.startsWith(item))) {
          return false;
        }

        return true;
      }
    }
  });
};

export default config;
