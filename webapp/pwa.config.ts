export const pwaOptions = {
  registerType: 'autoUpdate',
  includeAssets: ['favicon.svg', 'pwa-icon.svg'],
  manifest: {
    name: 'Exan - AI Exam Scanner',
    short_name: 'Exan',
    description: 'Scan and compare exams with AI.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#f8f9fa',
    theme_color: '#f8f9fa',
    categories: ['education', 'productivity'],
    icons: [
      {
        src: '/pwa-icon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
        purpose: 'any maskable',
      },
    ],
  },
  workbox: {
    globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest}'],
    navigateFallbackDenylist: [/^\/api(?:\/|$)/],
    runtimeCaching: [
      {
        urlPattern: /\/api(?:\/|$)/,
        handler: 'NetworkOnly',
      },
    ],
  },
}
