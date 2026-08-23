import React, { useMemo, useState } from 'react'
import { Check, ChevronRight, Copy, GitCompare, MessageSquare, Move, RotateCcw, Send, Sparkles } from 'lucide-react'

// This is a presentation layer over the certified Creative Intelligence and
// Creative Studio sources. Sample cards are intentionally labeled; no scores
// or business outcomes are invented when a canonical source is unavailable.
const SAMPLE_TERRITORIES = [
  { id: 'a', label: 'Territory A', title: 'Funding clarity, without the fog', audience: 'Sample audience', message: 'Make the next readiness step feel understandable.', cta: 'See your next step', source: 'Sample concept' },
  { id: 'b', label: 'Territory B', title: 'Build the business lenders can trust', audience: 'Sample audience', message: 'Turn preparation into visible momentum.', cta: 'Review readiness', source: 'Sample concept' },
  { id: 'c', label: 'Territory C', title: 'A calmer path to capital', audience: 'Sample audience', message: 'Replace uncertainty with a clear sequence of actions.', cta: 'Start the review', source: 'Sample concept' },
]

export default function NexusCreativeStudioWorkspace({ onAskHermes, onReview }) {
  const [selected, setSelected] = useState('a')
  const [compare, setCompare] = useState(false)
  const [critique, setCritique] = useState(false)
  const [variation, setVariation] = useState(0)
  const selectedConcept = useMemo(() => SAMPLE_TERRITORIES.find((item) => item.id === selected), [selected])

  return <section className="nx2-creative-workspace" aria-label="Creative Studio workspace">
    <div className="nx2-creative-toolbar">
      <div><div className="nx2-eyebrow">CREATIVE STUDIO / SAMPLE WORKSPACE</div><h3>Shape the work, then send the strongest direction to review.</h3><p>Canonical Creative Intelligence remains the source for novelty, diversity, and similarity checks.</p></div>
      <span className="nx2-creative-source"><Sparkles size={14} /> Creative Intelligence · connected source</span>
    </div>
    <div className="nx2-creative-actions">
      <button type="button" onClick={() => setCompare((value) => !value)}><GitCompare size={15} /> {compare ? 'Exit compare' : 'Compare territories'}</button>
      <button type="button" onClick={() => setCritique((value) => !value)}><MessageSquare size={15} /> {critique ? 'Hide critique' : 'Show critique'}</button>
      <button type="button" onClick={() => setVariation((value) => value + 1)}><Copy size={15} /> Create variation</button>
      {onAskHermes && <button type="button" onClick={onAskHermes}><Move size={15} /> Ask Nexus</button>}
    </div>
    <div className={`nx2-creative-canvas ${compare ? 'is-comparing' : ''}`}>
      <div className="nx2-creative-territories">
        {SAMPLE_TERRITORIES.map((concept) => <button type="button" key={concept.id} className={`nx2-creative-territory ${selected === concept.id ? 'selected' : ''}`} onClick={() => setSelected(concept.id)}>
          <div className="nx2-creative-art"><span>{concept.label}</span><strong>{concept.title}</strong><small>Visual preview · SAMPLE</small></div>
          <div className="nx2-creative-territory-copy"><strong>{concept.message}</strong><span>{concept.audience} · CTA: {concept.cta}</span><small>{concept.source} · novelty: UNKNOWN · similarity: UNKNOWN</small></div>
        </button>)}
      </div>
      <aside className="nx2-creative-inspector">
        <div className="nx2-eyebrow">{selectedConcept.label} / INSPECTOR</div>
        <h4>{selectedConcept.title}</h4>
        <div className="nx2-creative-inspector-row"><span>Audience</span><b>{selectedConcept.audience}</b></div>
        <div className="nx2-creative-inspector-row"><span>Message</span><b>{selectedConcept.message}</b></div>
        <div className="nx2-creative-inspector-row"><span>Creative Intelligence</span><b>Review pending</b></div>
        {critique && <div className="nx2-creative-critique"><MessageSquare size={15} /><div><strong>Critique · SAMPLE</strong><p>Check distinction between territories and validate the CTA hierarchy against canonical evidence.</p></div></div>}
        {variation > 0 && <div className="nx2-creative-variation"><RotateCcw size={15} /><span>Variation {variation} staged locally for review.</span></div>}
        <div className="nx2-creative-inspector-actions"><button type="button" onClick={() => setVariation((value) => value + 1)}><Check size={14} /> Select direction</button><button type="button" onClick={onReview}><Send size={14} /> Send to Ray Review</button></div>
      </aside>
    </div>
  </section>
}
