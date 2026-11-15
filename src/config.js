/**
 * Global Configuration for Lunar Landing Site Navigator.
 *
 * In development mode (import.meta.env.DEV === true), falls back to
 * http://127.0.0.1:8000 when VITE_API_BASE_URL is not set.
 *
 * In production builds (import.meta.env.PROD === true), requires
 * VITE_API_BASE_URL to be set explicitly at build time. If it is missing,
 * API_BASE_URL is set to null and the application must display a
 * configuration error rather than silently calling localhost.
 */

function resolveApiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASE_URL;

  if (raw && typeof raw === 'string' && raw.trim().length > 0) {
    // Normalize: strip trailing slashes
    return raw.trim().replace(/\/+$/, '');
  }

  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:8000';
  }

  // Production with no configured URL — return null so the app can show an error
  return null;
}

export const API_BASE_URL = resolveApiBaseUrl();
