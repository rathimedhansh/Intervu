import { useState } from 'react'

const WIDTH = 640
const HEIGHT = 220
const PADDING = { top: 20, right: 16, bottom: 28, left: 32 }
const Y_TICKS = [0, 25, 50, 75, 100]

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

// Dependency-free SVG line chart (no charting library in this project).
// Single series, so no legend — the card title already names what's plotted.
function ProgressChart({ points }) {
  const [hoverIndex, setHoverIndex] = useState(null)

  const innerWidth = WIDTH - PADDING.left - PADDING.right
  const innerHeight = HEIGHT - PADDING.top - PADDING.bottom

  const xFor = (index) =>
    points.length === 1
      ? PADDING.left + innerWidth / 2
      : PADDING.left + (index / (points.length - 1)) * innerWidth
  const yFor = (score) => PADDING.top + innerHeight - (score / 100) * innerHeight

  const linePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${xFor(index)} ${yFor(point.score)}`)
    .join(' ')

  const xLabelStride = Math.max(1, Math.ceil(points.length / 6))

  function handleMove(event) {
    if (points.length === 0) return
    const rect = event.currentTarget.getBoundingClientRect()
    const relativeX = ((event.clientX - rect.left) / rect.width) * WIDTH
    let nearest = 0
    let nearestDistance = Infinity
    points.forEach((_, index) => {
      const distance = Math.abs(xFor(index) - relativeX)
      if (distance < nearestDistance) {
        nearestDistance = distance
        nearest = index
      }
    })
    setHoverIndex(nearest)
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null
  const lastPoint = points[points.length - 1]

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id="progress-line-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3d7fff" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#3d7fff" stopOpacity="0" />
          </linearGradient>
        </defs>

        {Y_TICKS.map((tick) => (
          <g key={tick}>
            <line
              x1={PADDING.left}
              x2={WIDTH - PADDING.right}
              y1={yFor(tick)}
              y2={yFor(tick)}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="1"
            />
            <text
              x={PADDING.left - 8}
              y={yFor(tick)}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-ink-faint text-[10px]"
            >
              {tick}
            </text>
          </g>
        ))}

        {points.length > 1 && (
          <path
            d={`${linePath} L ${xFor(points.length - 1)} ${yFor(0)} L ${xFor(0)} ${yFor(0)} Z`}
            fill="url(#progress-line-fill)"
            stroke="none"
          />
        )}

        {points.length > 1 && (
          <path
            d={linePath}
            fill="none"
            stroke="#3d7fff"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {points.map((point, index) => (
          <circle
            key={point.interview_id}
            cx={xFor(index)}
            cy={yFor(point.score)}
            r={hoverIndex === index ? 5.5 : 3.5}
            fill="#08090c"
            stroke="#3d7fff"
            strokeWidth="2"
          />
        ))}

        {lastPoint && (
          <text
            x={xFor(points.length - 1)}
            y={yFor(lastPoint.score) - 12}
            textAnchor="end"
            className="fill-cyan text-[11px] font-semibold"
          >
            {lastPoint.score}
          </text>
        )}

        {hoverIndex !== null && (
          <line
            x1={xFor(hoverIndex)}
            x2={xFor(hoverIndex)}
            y1={PADDING.top}
            y2={HEIGHT - PADDING.bottom}
            stroke="rgba(255,255,255,0.16)"
            strokeWidth="1"
          />
        )}

        {points.map((point, index) => {
          const isLast = index === points.length - 1
          if (!isLast && index % xLabelStride !== 0) return null
          return (
            <text
              key={`x-${point.interview_id}`}
              x={xFor(index)}
              y={HEIGHT - PADDING.bottom + 16}
              textAnchor="middle"
              className="fill-ink-faint text-[10px]"
            >
              {formatDate(point.date)}
            </text>
          )
        })}
      </svg>

      {hovered && (
        <div
          className="surface-card pointer-events-none absolute top-2 -translate-x-1/2 px-2.5 py-1.5 text-xs"
          style={{ left: `${(xFor(hoverIndex) / WIDTH) * 100}%` }}
        >
          <p className="font-semibold text-ink">{hovered.score}/100</p>
          <p className="text-ink-faint">{formatDate(hovered.date)}</p>
        </div>
      )}
    </div>
  )
}

export default ProgressChart
