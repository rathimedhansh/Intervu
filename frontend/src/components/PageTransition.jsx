import { motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'

// Subtle fade + rise on route change — keyed on pathname so it replays per
// navigation. Kept short and simple on purpose (see redesign brief: "DO NOT
// over-animate the application").
function PageTransition({ children }) {
  const location = useLocation()
  return (
    <motion.div
      key={location.pathname}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

export default PageTransition
