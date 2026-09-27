import fs from 'node:fs'
import postcss from 'postcss'

const sourcePath = process.argv[2] || 'src/client-v2/approved/generated.v4.css'
const source = fs.readFileSync(sourcePath, 'utf8')
const root = postcss.parse(source)
const namespace = '.goclear-approved-portal'

root.walkRules((rule) => {
  if (!rule.selector || (rule.parent?.type === 'atrule' && rule.parent.name === 'keyframes')) return
  rule.selectors = rule.selectors.map((selector) => {
    const trimmed = selector.trim()
    if (trimmed === ':root') return namespace
    if (trimmed === '::backdrop') return `${namespace} ::backdrop`
    if (trimmed === '*') return `${namespace} *`
    return `${namespace} ${trimmed}`
  })
})

// The host app contains legacy unlayered rules such as `.grid` and `.hidden`.
// Keep the Tailwind 4 declarations scoped, but flatten its internal layers so
// the scoped approved surface wins only inside its own visual root.
root.walkAtRules('layer', (layer) => {
  layer.replaceWith(...(layer.nodes || []))
})

fs.writeFileSync('src/client-v2/approved/generated.scoped.css', root.toString())
