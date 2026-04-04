import { useState, useCallback } from 'react'

const MODES = ['compact', 'half', 'full']

export function useResize() {
  const [mode, setMode] = useState('compact')

  const cycleMode = useCallback(() => {
    setMode((prev) => {
      const idx = MODES.indexOf(prev)
      return MODES[(idx + 1) % MODES.length]
    })
  }, [])

  return { mode, cycleMode }
}
