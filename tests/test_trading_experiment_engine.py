import unittest
from scripts.trading.trading_experiment_engine import compare_engine_parity, normalize_result

class ExperimentEngineContractTests(unittest.TestCase):
    def test_normalizes_native_result(self):
        row=normalize_result({'strategy_id':'s','instrument':'EUR_USD','timeframe':'H1','trade_count':12,'net_result_equity_fraction':.1,'max_drawdown_fraction':.04,'data_provider':'OANDA_PRACTICE'},engine='NEXUS_NATIVE',engine_version='1',experiment_id='e')
        self.assertEqual(row['symbol'],'EUR_USD'); self.assertEqual(row['trades'],12); self.assertEqual(row['net_return'],.1)
    def test_parity_fails_closed_when_signal_stream_missing_or_different(self):
        a={'signal_timestamps':['t1'],'trades':1,'win_rate':1,'profit_factor':2,'expectancy':1,'net_return':1,'max_drawdown':0}
        missing=compare_engine_parity(a,{k:v for k,v in a.items() if k!='signal_timestamps'})
        self.assertEqual(missing['engine_parity_status'],'FAIL'); self.assertFalse(missing['lesson_eligible'])
        b={**a,'signal_timestamps':['t2']}
        self.assertIn('SIGNAL_TIMESTAMPS_DIFFER',compare_engine_parity(a,b)['reasons'])
    def test_matching_results_are_eligible_for_review(self):
        a={'signal_timestamps':['t1'],'trades':1,'win_rate':1,'profit_factor':2,'expectancy':1,'net_return':1,'max_drawdown':0}
        self.assertTrue(compare_engine_parity(a,a.copy())['lesson_eligible'])

if __name__=='__main__': unittest.main()
