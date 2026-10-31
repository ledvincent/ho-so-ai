import copy
import pytest
from api import profiles


def unknown():return dict(value=None,status='unknown',source_refs=[],conflicts=[])
def citation():return dict(source_id='primary',locator='identity',quote='1.001146')
def predicate(key='current_stay_basis',value='visa'):
    return dict(operator='eq',criterion_key=key,values=[value],children=[],source_refs=[citation()])


@pytest.fixture
def specimen():
    source=dict(source_id='primary',locator='identity',text='1.001146\nOfficial procedure')
    data={key:unknown() for key in ('procedure_code','official_name','purpose','outcome','jurisdiction','authority','authority_level','effective_from','effective_to')}
    data.update({key:[] for key in ('action_type','aliases','example_requests','applicant_categories','eligibility_rules','exclusions','submission_channels','required_documents','supersedes','decision_criteria','form_relationships','missing_information','issues')})
    for key,value in [('procedure_code','1.001146'),('official_name','Official procedure')]:
        data[key]=dict(value=value,status='supported',source_refs=[dict(source_id='primary',locator='identity',quote=value)],conflicts=[])
    for key in ('aliases','example_requests'):
        data[key]=[dict(text=lang+' generated routing',language=lang,origin='generated',source_refs=[]) for lang in ('vi','en')]
    return data,[source]


def validate(data,sources):return profiles.validate_profile(data,sources,'1.001146','Official procedure',[])


def test_unknown_is_preserved_and_generated_routing_is_separate(specimen):
    profile,count=validate(*specimen)
    assert count==2 and profile['purpose']['value'] is None
    assert profile['aliases'][0]['origin']=='generated'


def test_invented_quote_rejected(specimen):
    data,sources=specimen
    data['purpose']=dict(value='Guessed',status='supported',source_refs=[{**citation(),'quote':'not in the source'}],conflicts=[])
    with pytest.raises(ValueError,match='Unverifiable'):validate(data,sources)


def test_requirement_notes_need_citations_not_fake_document_entries(specimen):
    data, sources = specimen
    sources.append(dict(source_id='primary',locator='requirement:0',text='A special exception'))
    with pytest.raises(ValueError,match='requirement:0'):
        profiles.validate_source_coverage(data,sources)
    data['eligibility_rules'] = [dict(statement=dict(source_refs=[
        dict(source_id='primary',locator='requirement:0',quote='A special exception')]))]
    profiles.validate_source_coverage(data,sources)
    sources.append(dict(source_id='primary',locator='method:0',text='Online'))
    with pytest.raises(ValueError,match='method:0'):
        profiles.validate_source_coverage(data,sources)


def test_supported_fact_needs_evidence(specimen):
    data,sources=specimen
    data['purpose']=dict(value='Guessed',status='supported',source_refs=[],conflicts=[])
    with pytest.raises(ValueError,match='lacks evidence'):validate(data,sources)


def test_form_date_cannot_become_procedure_date(specimen):
    data,sources=specimen
    sources.append(dict(source_id='form:a',locator='page:1',text='2026-07-01'))
    data['effective_from']=dict(value='2026-07-01',status='supported',source_refs=[dict(source_id='form:a',locator='page:1',quote='2026-07-01')],conflicts=[])
    with pytest.raises(ValueError,match='form dates'):validate(data,sources)


def test_unanswered_condition_is_unknown_not_false():
    rule=predicate()
    assert profiles.evaluate(rule,{}) is None
    assert profiles.evaluate(rule,{'current_stay_basis':'unknown'}) is None
    assert profiles.evaluate(rule,{'current_stay_basis':'visa'}) is True
    assert profiles.evaluate(rule,{'current_stay_basis':'visa_exemption'}) is False


def test_and_or_not_preserve_three_valued_logic():
    a=predicate();b=predicate('authority_level','central')
    group=dict(operator='and',children=[a,b])
    assert profiles.evaluate(group,{'current_stay_basis':'visa'}) is None
    assert profiles.evaluate(group,{'current_stay_basis':'different'}) is False
    group['operator']='or'
    assert profiles.evaluate(group,{'current_stay_basis':'visa'}) is True
    assert profiles.evaluate(dict(operator='not',children=[a]),{}) is None


def test_unanswerable_eligibility_key_rejected(specimen):
    data,sources=specimen
    data['eligibility_rules']=[dict(rule_id='r1',statement=unknown(),condition=predicate(),exceptions=[])]
    with pytest.raises(ValueError,match='Missing clarification'):validate(data,sources)


def test_baseline_changes_when_prompt_changes(monkeypatch):
    from api.baseline import contract
    before=contract()
    assert contract()['id']==before['id']
    monkeypatch.setattr(profiles,'PROMPT',profiles.PROMPT+' new extraction rule')
    assert contract()['id']!=before['id']
