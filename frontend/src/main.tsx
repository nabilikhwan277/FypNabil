import { MotionConfig } from 'framer-motion'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// Fonts are bundled (no Google Fonts request), so the app also works offline in class.
import '@fontsource-variable/plus-jakarta-sans'
import '@fontsource/noto-naskh-arabic/400.css'
import '@fontsource/noto-naskh-arabic/700.css'
import './index.css'
import App from './App.tsx'
import { ChatProvider } from './chat/ChatContext.tsx'
import { ScriptProvider } from './i18n/ScriptContext.tsx'
import { AdminProvider } from './session/AdminContext.tsx'
import { ProgressProvider } from './session/ProgressContext.tsx'
import { StudentProvider } from './session/StudentContext.tsx'
import { SoundProvider } from './sound/SoundContext.tsx'
import { ThemeProvider } from './theme/ThemeContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Framer Motion follows the device's "reduce motion" setting (CSS animations use index.css). */}
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <ThemeProvider>
          <ScriptProvider>
            <SoundProvider>
              <AdminProvider>
                <StudentProvider>
                  <ProgressProvider>
                    <ChatProvider>
                      <App />
                    </ChatProvider>
                  </ProgressProvider>
                </StudentProvider>
              </AdminProvider>
            </SoundProvider>
          </ScriptProvider>
        </ThemeProvider>
      </BrowserRouter>
    </MotionConfig>
  </StrictMode>,
)
