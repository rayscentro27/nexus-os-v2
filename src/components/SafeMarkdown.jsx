import React from 'react'

// Allow-listed presentation for agent/report text. HTML is never interpreted.
function inline(text) {
  const parts = String(text || '').split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)/g)
  return parts.map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>
    if ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) return <em key={index}>{part.slice(1, -1)}</em>
    return <React.Fragment key={index}>{part}</React.Fragment>
  })
}

export default function SafeMarkdown({ children, className = '' }) {
  const lines = String(children || '').split(/\r?\n/)
  const blocks = []
  let list = null
  const flushList = () => {
    if (!list) return
    const Element = list.ordered ? 'ol' : 'ul'
    blocks.push(<Element key={`list-${blocks.length}`}>{list.items.map((item, index) => <li key={index}>{inline(item)}</li>)}</Element>)
    list = null
  }
  lines.forEach((line, index) => {
    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    const bullet = line.match(/^[-*]\s+(.+)$/)
    const ordered = line.match(/^\d+[.)]\s+(.+)$/)
    if (bullet || ordered) {
      const isOrdered = Boolean(ordered)
      if (!list || list.ordered !== isOrdered) { flushList(); list = { ordered: isOrdered, items: [] } }
      list.items.push((bullet || ordered)[1])
      return
    }
    flushList()
    if (heading) {
      const Element = `h${heading[1].length}`
      blocks.push(<Element key={index}>{inline(heading[2])}</Element>)
    } else if (line.trim()) {
      blocks.push(<p key={index}>{inline(line)}</p>)
    } else if (blocks.length) {
      blocks.push(<br key={index} />)
    }
  })
  flushList()
  return <div className={`nexus-safe-markdown ${className}`.trim()}>{blocks}</div>
}
