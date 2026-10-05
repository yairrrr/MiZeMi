import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import '@fontsource-variable/rubik/wght.css'
import '@fontsource-variable/fredoka/wght.css'

import { installSoundEffects } from './audio/sound'
import { App } from './components/App'
import './styles.css'

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('MiZeMi root element was not found')
}

installSoundEffects()

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
