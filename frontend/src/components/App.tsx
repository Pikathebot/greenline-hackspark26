import { useEffect } from 'react'
import { useUiStore } from '../state/uiStore'
import { CenterColumn } from './CenterColumn'
import { DebugDrawer } from './DebugDrawer'
import { LeftColumn } from './LeftColumn'
import { OfflineBanner } from './OfflineBanner'
import { RightColumn } from './RightColumn'
import { TopBarShell } from './TopBarShell'

export function App() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === 'Backquote') useUiStore.getState().toggleDebug()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="grid h-screen grid-rows-[64px_1fr] bg-bg text-text">
      <OfflineBanner />
      <TopBarShell />
      <div className="grid min-h-0 grid-rows-[minmax(0,1fr)] grid-cols-[300px_1fr_420px] [@media(max-height:1000px)]:grid-cols-[264px_1fr_372px]">
        <LeftColumn />
        <CenterColumn />
        <RightColumn />
      </div>
      <DebugDrawer />
    </div>
  )
}
