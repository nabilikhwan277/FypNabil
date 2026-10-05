import { useCallback, useEffect, useState } from 'react'

const supported = typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window

/** A Malay voice, or an Indonesian one (close enough to read Rumi aloud). */
function pickVoice(): SpeechSynthesisVoice | null {
  if (!supported) return null
  const voices = window.speechSynthesis.getVoices()
  return voices.find((v) => /^ms([-_]|$)/i.test(v.lang)) ?? voices.find((v) => /^id([-_]|$)/i.test(v.lang)) ?? null
}

/**
 * Read text aloud with the browser's speech synthesis. `available` is false
 * when the device has no Malay/Indonesian voice, so callers can hide the button.
 * Voices read Latin script only: pass Rumi text.
 */
export function useSpeech() {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(pickVoice)
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => {
    if (!supported) return
    const synth = window.speechSynthesis
    const update = () => setVoice(pickVoice())
    update()
    synth.addEventListener('voiceschanged', update)
    return () => {
      synth.removeEventListener('voiceschanged', update)
      synth.cancel()
    }
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!supported || !voice || !text.trim()) return
      const synth = window.speechSynthesis
      synth.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.voice = voice
      u.lang = voice.lang
      u.rate = 0.9
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      setSpeaking(true)
      synth.speak(u)
    },
    [voice],
  )

  const stop = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [])

  return { available: voice !== null, speaking, speak, stop }
}
