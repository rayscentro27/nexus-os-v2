#!/usr/bin/env python3
from pathlib import Path
import importlib.util,sys
root=Path(__file__).resolve().parents[2]; module_path=root/'scripts/credit/funding_readiness_credit_analysis.py'; spec=importlib.util.spec_from_file_location('analysis',module_path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sample={'confidence':'medium','accounts':[{'bureau':'experian','furnisherName':'Card A','accountNumberMasked':'****1234','itemType':'utilization','utilizationPercent':72,'confidence':'high'},{'bureau':'equifax','furnisherName':'Card B','itemType':'other','confidence':'high'}],'inquiries':[{'bureau':'experian','company':'Test Bank','confidence':'medium'}],'personalInfoVariations':[],'warnings':[]}; out=m.analyze_credit_for_funding_readiness(sample)
checks={'categories generated':out['utilizationActions'] and out['inquiryReviews'],'not every account dispute':len(out['reportItemReviews'])<len(sample['accounts']),'confidence exists':'confidenceSummary' in out,'recommended actions exist':bool(out['recommendedNextSteps']),'letter eligibility limited':not out['utilizationActions'][0]['letterEligible'],'TypeScript shared engine exists':(root/'src/lib/fundingReadinessCreditAnalysis.ts').exists()}
for n,v in checks.items(): print(('PASS' if v else 'FAIL')+': '+n)
sys.exit(0 if all(checks.values()) else 1)
