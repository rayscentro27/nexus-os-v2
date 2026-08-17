export const polarToCartesian = (cx: number, cy: number, radius: number, angleDeg: number) => {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) }
}

export const describeArc = (cx: number, cy: number, radius: number, startAngle: number, endAngle: number) => {
  const start = polarToCartesian(cx, cy, radius, endAngle)
  const end = polarToCartesian(cx, cy, radius, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1'
  return ['M', start.x, start.y, 'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(' ')
}

export const clamp = (value: number, min = 0, max = 100) => Math.max(min, Math.min(max, value))

export const scoreTone = (score: number): 'emerald' | 'brand' | 'amber' | 'red' => {
  if (score >= 80) return 'emerald'
  if (score >= 60) return 'brand'
  if (score >= 40) return 'amber'
  return 'red'
}