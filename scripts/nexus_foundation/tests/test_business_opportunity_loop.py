from nexus_foundation.business_opportunity_loop import economic_model, score
def test_economic_model_labels_unknowns():
 m=economic_model(); assert m['scenarios']['BASE']['revenue']==10890; assert m['scenarios']['BASE']['cac']=='UNKNOWN'; assert m['unit_economics']['ltv']=='NOT_COMPUTED_WITHOUT_RETENTION'
def test_score_is_bounded(): assert 0 <= score() <= 100
