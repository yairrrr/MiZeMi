import { useEffect, useRef } from 'react'

/** Focus a new stage once, never on roster/timer updates or outside-game controls. */
export function useStageFocus(stage: string) {
  const root = useRef<HTMLElement>(null)
  useEffect(() => {
    const container = root.current
    if (!container) return
    const active = document.activeElement
    if (active && active !== document.body && !container.contains(active)) return
    const heading = container.querySelector<HTMLElement>('.stage h2')
    if (heading) {
      heading.tabIndex = -1
      heading.focus()
    }
  }, [stage])
  return root
}
