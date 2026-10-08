import type { CSSProperties, ReactNode } from 'react'

interface IconProps {
  size?: number
  style?: CSSProperties
}

function Svg({ size, style, children }: IconProps & { children: ReactNode }) {
  const s = size ? { width: size, height: size, ...style } : style
  return (
    <svg className="ico" viewBox="0 0 24 24" aria-hidden="true" style={s}>
      {children}
    </svg>
  )
}

export function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
      <rect width="30" height="30" rx="8" fill="var(--brand)" />
      <path
        d="M7 19.5l5-5 3.5 3L23 10"
        fill="none"
        stroke="var(--on-accent)"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
export const Circle = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="7" /></Svg>
export const Check = (p: IconProps) => <Svg {...p}><path d="M5 12.5l4.5 4.5L19 7.5" /></Svg>
export const Dash = (p: IconProps) => <Svg {...p}><path d="M5 12h3M10.5 12h3M16 12h3" /></Svg>
export const Cross = (p: IconProps) => <Svg {...p}><path d="M6.5 6.5l11 11M17.5 6.5l-11 11" /></Svg>
export const Warn = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 4l9 16H3z" />
    <path d="M12 10v4.5M12 17.5v.2" />
  </Svg>
)
const SHIELD = 'M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z'
export const ShieldFired = (p: IconProps) => (
  <Svg {...p}>
    <path d={SHIELD} />
    <path d="M9.5 9.5l5 5M14.5 9.5l-5 5" />
  </Svg>
)
export const ShieldClear = (p: IconProps) => (
  <Svg {...p}>
    <path d={SHIELD} />
    <path d="M9 12.2l2.2 2.2L15.5 10" />
  </Svg>
)
export const ShieldIdle = (p: IconProps) => <Svg {...p}><path d={SHIELD} /></Svg>
export const Play = (p: IconProps) => (
  <Svg {...p} style={{ fill: 'currentColor', stroke: 'none', ...p.style }}>
    <path d="M8 5.5v13l11-6.5z" />
  </Svg>
)
export const Person = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="8" r="3.5" />
    <path d="M5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5" />
  </Svg>
)
export const Doc = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7 3.5h7l4 4V20.5H7z" />
    <path d="M14 3.5v4h4" />
  </Svg>
)
