import {
  IconChartBar,
  IconClock,
  IconGrid,
  IconPlus,
  IconSettings,
  IconTarget,
  IconUser,
} from './icons'

// Shared between the desktop Sidebar and the mobile nav drawer so the two
// never drift out of sync. Grouped into sections so the sidebar reads as
// "product nav" vs "account", not one flat list.
export const NAV_GROUPS = [
  {
    label: 'Main',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: IconGrid, end: true },
      { to: '/setup', label: 'New Interview', icon: IconPlus },
      { to: '/history', label: 'Interview History', icon: IconClock },
      { to: '/performance', label: 'Performance', icon: IconChartBar },
      { to: '/practice', label: 'Practice', icon: IconTarget },
    ],
  },
  {
    label: 'Account',
    items: [
      { to: '/profile', label: 'Profile', icon: IconUser },
      { to: '/settings', label: 'Settings', icon: IconSettings },
    ],
  },
]

export const NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items)
