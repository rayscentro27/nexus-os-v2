import { runSafeOperationalCycle } from "../src/hermes/nexus/nexusAllDayResearchRunner";
console.log(JSON.stringify({...runSafeOperationalCycle(), closeout:true}, null, 2));
