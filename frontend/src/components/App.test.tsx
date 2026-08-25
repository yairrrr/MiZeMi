import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { App } from './App'

test('renders the MiZeMi application shell', () => {
  render(<App />)

  expect(screen.getByRole('heading', { level: 1, name: 'MiZeMi' })).toBeInTheDocument()
  expect(screen.getByText(/real-time group icebreaker/i)).toBeVisible()
})
