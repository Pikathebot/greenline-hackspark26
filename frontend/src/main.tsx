import '@fontsource/geist/400.css'
import '@fontsource/geist/500.css'
import '@fontsource/geist/600.css'
import '@fontsource/geist-mono/400.css'
import '@fontsource/geist-mono/500.css'
import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { bootstrap } from './app/bootstrap'
import { App } from './components/App'

// Module level (outside React) so StrictMode's double effects can't double it.
void bootstrap()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
