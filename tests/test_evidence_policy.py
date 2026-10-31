from api.evidence_policy import allowed,VERSION

def test_unknown_block_stays_blocked():
    assert not allowed(False,{},'run',1)

def test_review_only_applies_to_exact_run_and_profile():
    review=dict(policy=VERSION,access='source_attributed',run_id='run',profile_id=1)
    assert allowed(False,review,'run',1)
    assert not allowed(False,review,'other',1)
    assert not allowed(False,review,'run',2)
    assert not allowed(False,{**review,'access':'blocked'},'run',1)
