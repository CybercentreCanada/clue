/* eslint-disable no-console */
import react from '@vitejs/plugin-react-swc';
import { glob } from 'glob';
import path, { sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { extname, relative, resolve } from 'path';
import { defineConfig, loadEnv } from 'vite';
import dts from 'vite-plugin-dts';
import eslint from 'vite-plugin-eslint';
import tsconfigPaths from 'vite-tsconfig-paths';
import { configDefaults } from 'vitest/config';

// FIXME mui v5/6 doesn't play nice with esm. This only seems to apply to material icons, so we'll special case here.
// https://github.com/mui/material-ui/issues/35233
// function iconsMaterialPlugin(): Plugin {
//   console.log('Enabling iconsMaterialPlugin');

//   return {
//     name: 'icons-material',
//     transform(code, id) {
//       if (id.includes('@jsonforms/material-renderers') || id.includes('src/commons')) {
//         console.log(`Validating ${id} does not contain non-esm imports..`);
//         if (code.includes('icons-material/') || /icons-material["'];/.test(code)) {
//           const lineNumber =
//             code.split('\n').findIndex(line => line.includes('icons-material/') || /icons-material["'];/.test(line)) +
//             1;

//           console.log(`Non-esm icons-material import found at ${path.basename(id)}:${lineNumber}`);

//           const result = code
//             .replace(/icons-material\//g, 'icons-material/esm/')
//             .replace(/icons-material(["'];)/g, 'icons-material/esm$1');

//           const replacedLine = result.split('\n').find(line => line.includes('esm'));

//           console.log(`Replacement import: ${replacedLine}`);
//           return {
//             code: result
//           };
//         }
//       }
//     }
//   };
// }

const distPath = path.join(__dirname, 'dist');

// https://vitejs.dev/config/
const config = ({ mode }) => {
  process.env = { ...process.env, ...loadEnv(mode, process.cwd()) };

  const useMinify = !process.env.npm_package_version?.includes('dev');

  console.log('Building version:', process.env.npm_package_version);
  console.log('Using minification:', useMinify);

  return defineConfig({
    plugins: [
      eslint(),
      react(),
      tsconfigPaths(),
      dts({
        include: ['src/lib', 'src/api/lookup', 'src/lib/**/*.d.ts'],
        exclude: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
        copyDtsFiles: true,
        beforeWriteFile: (filePath, content) => {
          // Because of the truly masochistic approach I took to structuring this library,
          // We need to do some manual reordering of the types definitions files and imports.

          // No matter what, we remove the prepended "lib" folder section
          const newFilePath = filePath.replaceAll(`lib${sep}`, '');
          let newContent = content;

          // We calculate the offset in ../ folder navigation from the proposed file path to the root of the dist directory.
          // This looks something like: ../../
          const relativeOffset = (path.relative(path.dirname(newFilePath), distPath) || '.') + sep;

          // First, we check for any lib imports in the d.ts files - we strip the lib folder as seen above.
          if (content.includes('lib')) {
            // We use regex (scary, I know) to move from the previous absolute import
            // to a relative import, prepending the precalculated relative offset
            newContent = content.replace(/(['"])lib((\\)|\/)(.+?)(['"])/g, `"${relativeOffset}$4"`);
          }

          if (content.includes('api')) {
            // We use regex again to do the same thing, but for api types instead of standalone type declarations
            newContent = content.replace(/(['"])(api((\\)|\/)(.+?))(['"])/g, `"${relativeOffset}$2"`);
          }

          // The final product:
          // import X from 'lib/types/Y'; turns into import X from '../../types/Y';
          // import X from 'api/lookups/enrich'; turns into import X from '../../api/lookups/enrich';

          // We return the "fixed" types declaration to be written.
          return {
            filePath: newFilePath,
            content: newContent
          };
        }
      })
      // { ...iconsMaterialPlugin(), enforce: 'pre', apply: 'build' }
    ],
    publicDir: 'src/locales',
    build: {
      copyPublicDir: true,
      minify: useMinify,
      lib: {
        entry: resolve(__dirname, 'src/lib/main.ts'),
        formats: ['es']
      },
      rollupOptions: {
        external: [
          /@mui.*/,
          /@emotion.*/,
          /@jsonforms.*/,
          'i18next-browser-languagedetector',
          'i18next',
          'react',
          'react/jsx-runtime',
          'react-dom',
          'react-i18next',
          'react-markdown',
          'react-syntax-highlighter',
          'remark-gfm',
          '@microlink/react-json-view',
          '**/*.test.js',
          '**/*.test.ts',
          '**/*.spec.ts',
          '**/*.spec.ts',
          '**/__tests__/**',
          '**/tests/**'
        ],
        input: Object.fromEntries(
          glob
            .sync('src/lib/**/*.{ts,tsx}')
            .filter(file => !file.includes('.test.') && !file.includes('/tests/') && !file.endsWith('.d.ts'))
            .map(file => [
              // The name of the entry point
              // lib/nested/foo.ts becomes nested/foo
              relative('src/lib', file.slice(0, file.length - extname(file).length)),
              // The absolute path to the entry file
              // lib/nested/foo.ts becomes /project/lib/nested/foo.ts
              fileURLToPath(new URL(file, import.meta.url))
            ])
        ),
        plugins: [],
        output: {
          assetFileNames: 'assets/[name][extname]',
          entryFileNames: '[name].js'
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
          'src/commons/**'
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
      }
    }
  });
};

export default config;
