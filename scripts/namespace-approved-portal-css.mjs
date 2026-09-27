import fs from 'node:fs'
import postcss from 'postcss'

const source = fs.readFileSync('src/client-v2/approved/generated.css', 'utf8')
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

fs.writeFileSync('src/client-v2/approved/generated.scoped.css', root.toString())
