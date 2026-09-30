import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { LanguageProvider } from './lib/i18n'

type TauriWindow = Window & {
  __TAURI_INTERNALS__?: {
    invoke<T>(command: string): Promise<T>
  }
}

async function configureDesktopApi() {
  const invoke = (window as TauriWindow).__TAURI_INTERNALS__?.invoke
  if (!invoke) return

  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const config = await invoke<{ base_url: string; secret: string }>('api_config')
      window.__EXAN_API_BASE__ = config.base_url
      window.__EXAN_API_SECRET__ = config.secret
      return
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100))
    }
  }
  throw new Error('The local inference service did not start.')
}

await configureDesktopApi()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LanguageProvider>
      <App />
    </LanguageProvider>
  </StrictMode>,
)
