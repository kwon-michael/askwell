import { timeAgo } from './time'

// Muted, warm tones that sit with the clay accent. Picked per username so a
// person keeps the same colour everywhere.
const AVATAR_COLORS = ['#c15f3c', '#8a7350', '#5d7a68', '#6a6f8c', '#94687a', '#7d8456']

function colorFor(name: string): string {
  let hash = 0
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

export function Avatar({ name, size = 22 }: { name: string; size?: number }) {
  return (
    <span
      className="avatar"
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.45,
        background: colorFor(name),
      }}
    >
      {name.slice(0, 1).toUpperCase()}
    </span>
  )
}

export function Byline({ name, at, size }: { name: string; at: string; size?: number }) {
  return (
    <span className="meta">
      <Avatar name={name} size={size} />
      <span>{name}</span>
      <span className="dot" />
      <time dateTime={at}>{timeAgo(at)}</time>
    </span>
  )
}

export function ChevronUp() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 10 8 5.5 12.5 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function ArrowLeft() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M13 8H3m0 0 4.5-4.5M3 8l4.5 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
