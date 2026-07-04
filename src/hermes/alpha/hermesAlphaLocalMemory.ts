export type AlphaMessage={id:string;role:"ray"|"alpha";text:string;createdAt:string;mode:string};
const KEY="nexus-alpha-conversation-v1";
export function loadAlphaMemory():AlphaMessage[]{try{return JSON.parse(localStorage.getItem(KEY)||"[]")}catch{return []}}
export function saveAlphaMemory(messages:AlphaMessage[]){localStorage.setItem(KEY,JSON.stringify(messages.slice(-100)))}
export function clearAlphaMemory(){localStorage.removeItem(KEY)}
export function exportAlphaSession(messages:AlphaMessage[]){return JSON.stringify({label:"Alpha local session export — no client data",exportedAt:new Date().toISOString(),messages},null,2)}
