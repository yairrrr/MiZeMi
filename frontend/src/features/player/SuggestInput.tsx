import { type InputHTMLAttributes, type KeyboardEvent, useEffect, useRef, useState } from 'react'

import { fetchSuggestions } from '../../api/roomApi'

const DEBOUNCE_MS = 150

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'id'> & {
  id: string
  field: string
  value: string
  onValueChange: (value: string) => void
}

/** Text input with an ARIA combobox list of up to five server completions. */
export function SuggestInput({ id, field, value, onValueChange, maxLength, disabled, ...inputProps }: Props) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  // Picking a suggestion sets the value; don't re-query for the picked name.
  const picked = useRef<string | null>(null)
  const listId = `${id}-suggestions`

  useEffect(() => {
    const query = value.trim()
    if (query === '' || picked.current === value || disabled) {
      setSuggestions([])
      return
    }
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      const found = await fetchSuggestions(field, query, controller.signal)
      if (controller.signal.aborted) return
      // A suggestion the field would reject is no help.
      const usable = found.filter((name) => maxLength === undefined || name.length <= maxLength)
      setSuggestions(usable)
      setActive(-1)
    }, DEBOUNCE_MS)
    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [field, value, maxLength, disabled])

  const expanded = open && suggestions.length > 0

  function choose(name: string) {
    picked.current = name
    onValueChange(name)
    setSuggestions([])
    setOpen(false)
    setActive(-1)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!expanded) {
      if (event.key === 'ArrowDown' && suggestions.length > 0) {
        event.preventDefault()
        setOpen(true)
      }
      return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const last = suggestions.length - 1
      setActive((current) => event.key === 'ArrowDown'
        ? (current >= last ? 0 : current + 1)
        : (current <= 0 ? last : current - 1))
    } else if (event.key === 'Enter' && active >= 0 && active < suggestions.length) {
      event.preventDefault()
      choose(suggestions[active])
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      setActive(-1)
    }
  }

  return (
    <div className="suggest">
      <input
        {...inputProps}
        id={id}
        value={value}
        maxLength={maxLength}
        disabled={disabled}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={listId}
        aria-activedescendant={expanded && active >= 0 && active < suggestions.length ? `${listId}-${active}` : undefined}
        onChange={(event) => {
          picked.current = null
          setOpen(true)
          onValueChange(event.target.value)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={handleKeyDown}
      />
      <ul id={listId} role="listbox" className="suggest-list" hidden={!expanded}>
        {suggestions.map((name, index) => (
          <li
            key={name}
            id={`${listId}-${index}`}
            role="option"
            dir="auto"
            aria-selected={index === active}
            className={index === active ? 'active' : undefined}
            // Keep focus in the input so blur doesn't close the list before the pick.
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => choose(name)}
          >
            {name}
          </li>
        ))}
      </ul>
    </div>
  )
}
