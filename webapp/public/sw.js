const CACHE_NAME = 'exan-shell-v1'
const APP_SHELL = ['/', '/index.html', '/favicon.svg', '/pwa-icon.svg']

function getBundleAssets(html) {
  const assets = new Set()
  const tags = html.matchAll(/<(script|link)\b([^>]*)>/gi)

  for (const [, tagName, attributes] of tags) {
    const values = {}
    for (const [, name, doubleQuoted, singleQuoted, unquoted] of attributes.matchAll(
      /([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g,
    )) {
      values[name.toLowerCase()] = doubleQuoted || singleQuoted || unquoted
    }

    const assetPath = tagName.toLowerCase() === 'script' ? values.src : values.href
    if (!assetPath || !assetPath.startsWith('/') || assetPath.startsWith('//')) continue

    const url = new URL(assetPath, self.location.origin)
    if (
      url.origin === self.location.origin &&
      /\.(?:m?js|css)$/i.test(url.pathname)
    ) {
      assets.add(url.href)
    }
  }

  return [...assets]
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      await cache.addAll(APP_SHELL)
      const index = await cache.match('/index.html')
      if (!index) throw new Error('App shell index.html was not cached')

      const bundleAssets = getBundleAssets(await index.text())
      await cache.addAll(bundleAssets)
    }).then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith('exan-shell-') && key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      ),
    ).then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)

  if (
    request.method !== 'GET' ||
    url.origin !== self.location.origin ||
    /^\/api(?:\/|$)/.test(url.pathname)
  ) {
    return
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const cachedPage = await caches.match('/index.html')
        return cachedPage || Response.error()
      }),
    )
    return
  }

  if (['script', 'style', 'image', 'font'].includes(request.destination)) {
    const networkRequest = fetch(request).then((response) => {
      if (!response.ok) return response

      const copy = response.clone()
      return caches.open(CACHE_NAME).then((cache) =>
        cache.put(request, copy).then(
          () => response,
          () => response,
        ),
      ).catch(() => response)
    })
    event.waitUntil(networkRequest.then(() => undefined, () => undefined))
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || networkRequest.catch(() => Response.error())
      }),
    )
  }
})
