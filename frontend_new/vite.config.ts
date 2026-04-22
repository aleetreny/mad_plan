import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUTPUT_FILES = ['eventos_madrid_all.json', 'noticias_madrid_all.json'];

function outputsPlugin() {
  return {
    name: 'madplan-outputs',
    configureServer(server: import('vite').ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || '';
        if (!url.startsWith('/outputs/')) {
          next();
          return;
        }

        const file = path.resolve(__dirname, '..', url.slice(1));
        if (!fs.existsSync(file)) {
          next();
          return;
        }

        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.setHeader('Cache-Control', 'no-store');
        res.end(fs.readFileSync(file));
      });
    },
    generateBundle() {
      for (const fileName of OUTPUT_FILES) {
        const absolutePath = path.resolve(__dirname, '..', 'outputs', fileName);
        if (!fs.existsSync(absolutePath)) continue;
        this.emitFile({
          type: 'asset',
          fileName: `outputs/${fileName}`,
          source: fs.readFileSync(absolutePath),
        });
      }
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    outputsPlugin(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    sourcemap: true,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
  },
});
