import { useHealthStore } from '../state/healthStore'

export function OfflineBanner() {
  const reachable = useHealthStore((s) => s.backendReachable)
  if (reachable !== false) return null
  return (
    <div
      role="alert"
      className="fixed inset-x-0 top-0 z-50 bg-danger px-4 py-2 text-center text-[15px] font-medium text-on-danger"
    >
      Backend offline: start uvicorn on :8000
    </div>
  )
}
