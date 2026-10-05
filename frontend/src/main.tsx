import { MotionConfig } from 'framer-motion'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import '@fontsource/nunito/400.css'
import '@fontsource/nunito/700.css'
import '@fontsource/nunito/900.css'
import '@fontsource/noto-naskh-arabic/400.css'
import '@fontsource/noto-naskh-arabic/700.css'
import './index.css'
import App from './App.tsx'
import { ScriptProvider } from './i18n/ScriptContext.tsx'
import { ProgressProvider } from './session/ProgressContext.tsx'
import { StudentProvider } from './session/StudentContext.tsx'
import { SoundProvider } from './sound/SoundContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Framer Motion follows the device's "reduce motion" setting (CSS animations use index.css). */}
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <ScriptProvider>
          <SoundProvider>
            <StudentProvider>
              <ProgressProvider>
                <App />
              </ProgressProvider>
            </StudentProvider>
          </SoundProvider>
        </ScriptProvider>
      </BrowserRouter>
    </MotionConfig>
  </StrictMode>,
)
