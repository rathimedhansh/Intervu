// Minimal, dependency-free stroke-icon set (24x24, currentColor) — avoids
// pulling in a full icon library for the handful of glyphs this UI needs.
// Every icon accepts the usual SVG props (className, etc).

function Icon({ children, ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  )
}

export function IconGrid(props) {
  return (
    <Icon {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </Icon>
  )
}

export function IconPlus(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v8M8 12h8" />
    </Icon>
  )
}

export function IconClock(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </Icon>
  )
}

export function IconChartBar(props) {
  return (
    <Icon {...props}>
      <path d="M4 20V10M12 20V4M20 20v-7" />
      <path d="M2 20h20" />
    </Icon>
  )
}

export function IconTarget(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4.2" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none" />
    </Icon>
  )
}

export function IconSettings(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.14.3.3.58.5.83" />
    </Icon>
  )
}

export function IconLogout(props) {
  return (
    <Icon {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5M21 12H9" />
    </Icon>
  )
}

export function IconMic(props) {
  return (
    <Icon {...props}>
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v4M8 22h8" />
    </Icon>
  )
}

export function IconChevronRight(props) {
  return (
    <Icon {...props}>
      <path d="M9 6l6 6-6 6" />
    </Icon>
  )
}

export function IconChevronLeft(props) {
  return (
    <Icon {...props}>
      <path d="M15 6l-6 6 6 6" />
    </Icon>
  )
}

export function IconCheck(props) {
  return (
    <Icon {...props}>
      <path d="M5 12.5l4.5 4.5L19 7" />
    </Icon>
  )
}

export function IconMenu(props) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Icon>
  )
}

export function IconClose(props) {
  return (
    <Icon {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Icon>
  )
}

export function IconTrendUp(props) {
  return (
    <Icon {...props}>
      <path d="M4 17l6-6 4 4 6-8" />
      <path d="M14 7h6v6" />
    </Icon>
  )
}

export function IconCheckCircle(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8.5 12.5l2.5 2.5 5-5" />
    </Icon>
  )
}

export function IconAlert(props) {
  return (
    <Icon {...props}>
      <path d="M12 9v4M12 17h.01" />
      <path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
    </Icon>
  )
}

export function IconSearch(props) {
  return (
    <Icon {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </Icon>
  )
}

export function IconTrash(props) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M9 7V4h6v3M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />
    </Icon>
  )
}

export function IconUser(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </Icon>
  )
}

export function IconSparkle(props) {
  return (
    <Icon {...props}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2" />
    </Icon>
  )
}

export function IconFileText(props) {
  return (
    <Icon {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M8 13h8M8 17h8M8 9h2" />
    </Icon>
  )
}

export function IconSkip(props) {
  return (
    <Icon {...props}>
      <path d="M5 4l10 8-10 8V4z" />
      <path d="M19 5v14" />
    </Icon>
  )
}

export function IconBell(props) {
  return (
    <Icon {...props}>
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 0 1-3.4 0" />
    </Icon>
  )
}
