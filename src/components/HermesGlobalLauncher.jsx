import React from 'react';
export default function HermesGlobalLauncher({ onOpen }) { return <button type="button" className="hermes-global-launcher" onClick={onOpen} aria-label="Ask Hermes without leaving this page"><span>✦</span><div><strong>Ask Hermes</strong><small>Chat here · stay on this page</small></div></button>; }
