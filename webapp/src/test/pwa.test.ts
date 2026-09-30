import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { pwaOptions } from '../../pwa.config'

describe('local PWA setup', () => {
  it('links the app shell to its generated manifest', () => {
    const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8')
    const document = new DOMParser().parseFromString(html, 'text/html')

    expect(document.querySelector('link[rel="manifest"]')?.getAttribute('href')).toBe(
      '/manifest.webmanifest',
    )
  })

  it('keeps API requests network-only and out of the app-shell fallback', () => {
    const apiUrl = 'http://localhost:3000/api/providers'
    const apiCachingRule = pwaOptions.workbox.runtimeCaching.find(({ urlPattern }) =>
      urlPattern instanceof RegExp ? urlPattern.test(apiUrl) : false,
    )

    expect(apiCachingRule?.handler).toBe('NetworkOnly')
    expect(
      pwaOptions.workbox.navigateFallbackDenylist.some((pattern) =>
        pattern.test('/api/providers'),
      ),
    ).toBe(true)
  })
})
