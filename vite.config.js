import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vendor code is split into long-cacheable chunks so no single bundle exceeds the 500 kB advisory.
function vendorChunk(id) {
  if (!id.includes('node_modules')) return undefined;
  if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'vendor-react';
  if (/node_modules\/(d3-[^/]+|victory-vendor|internmap|decimal\.js-light|recharts-scale|recharts)\//.test(id)) return 'vendor-charts';
  if (id.includes('node_modules/lucide-react')) return 'vendor-icons';
  return 'vendor';
}

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: { output: { manualChunks: vendorChunk } },
    chunkSizeWarningLimit: 500
  },
  server: {
    port: 3000,
    open: true
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    css: false,
    testTimeout: 15000
  }
});
