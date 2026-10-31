import json
from types import SimpleNamespace

import pytest
from api import assistant as a, rag


def test_comparison_question_does_not_select_the_mentioned_office():
    choices=[{'id':'a','label':'Provincial immigration office','codes':['a']},
             {'id':'b','label':'Central immigration department','codes':['b']}]
    for message in ['What is the central immigration department?',
                    'Explain provincial', 'whats the difference between these two?',
                    'Is provincial the right option for me?']:
        assert rag.match_choice(message,choices) is None
    assert rag.match_choice('central please',choices)['id']=='b'


def test_exact_reported_followup_gets_generated_answer_and_keeps_options(monkeypatch):
    source=a.Source(id='p1',title='Official source',url='https://example.test/province',
                    text='This procedure is handled by the provincial office.')
    pending=a.Retrieval(sources=[source],clarification='Which procedure?',
        choices=[a.Choice(id='a',label='Provincial'),a.Choice(id='b',label='Central')],
        retrieval_state='signed-state',original_question='Extend my stay',
        candidates=[dict(code='a',name='Provincial',source_ids=['p1'])])
    calls=[]
    def generate(request,evidence):
        calls.append(json.loads(a.build_messages(request,evidence)[1]['content']))
        return a.Generated(status='answered',answer='The first uses the provincial office. [p1]',source_ids=['p1']),'test'
    monkeypatch.setattr(a,'generate',generate)
    result=a.chat(a.ChatRequest(message='whats the difference between these two?',
        history=[a.Turn(role='user',content="I'm not sure")]),retriever=lambda request:pending)
    assert calls[0]['question']=='whats the difference between these two?'
    assert calls[0]['pending_selection']['original_goal']=='Extend my stay'
    assert len(result.choices)==2 and result.retrieval_state=='signed-state'
    assert result.procedure_code is None and result.model=='test' and result.citations


def test_general_explanation_can_answer_without_fake_citations():
    draft=a.Draft(status='answered',paragraphs=[a.Paragraph(
        text='An original is the issued document. A copy reproduces it.',source_ids=[],kind='general_guidance')])
    result=a.render_draft(draft,a.Retrieval())
    assert result.answer_basis=='general_guidance' and not result.source_ids
    schema=a.output_format(a.Retrieval())['json_schema']['schema']
    ids=schema['properties']['paragraphs']['items']['properties']['source_ids']
    assert ids['maxItems']==0 and 'enum' not in ids['items']


def test_unsourced_procedural_claim_is_rejected_even_with_general_intro():
    draft=a.Draft(status='answered',paragraphs=[
        a.Paragraph(text='I can help.',source_ids=[],kind='general_guidance'),
        a.Paragraph(text='This application costs 10 dollars.',source_ids=[],kind='procedure_fact')])
    with pytest.raises(ValueError,match='missing citations'):
        a.render_draft(draft,a.Retrieval())


def test_unready_candidate_stays_identified_without_exposing_facts(monkeypatch):
    candidates=[dict(code='1.000001',name='First'),dict(code='1.000002',name='Second')]
    monkeypatch.setattr(rag,'members',lambda *args:candidates)
    def evidence(release,code,query):
        if code=='1.000002': raise RuntimeError('Unreviewed')
        return [dict(id='s',title='Official',url='https://example.test',text='Source')]
    monkeypatch.setattr(rag,'evidence',evidence)
    result=rag.clarification(dict(release='r',codes=[c['code'] for c in candidates],asked=[],query='help',
        question=dict(text='Which?',choices=[])))
    assert len(result['sources'])==1
    assert result['candidates'][1]['evidence_available'] is False


def test_grouped_sources_keep_locators_and_all_sections():
    rows=[dict(id='one',title='Title',url='https://example.test',locator='section:0:name',body='First'),
          dict(id='two',title='Title',url='https://example.test',locator='section:1:requirements',body='Second')]
    sources=rag.grouped_sources(rows)
    assert len(sources)==1 and 'First' in sources[0]['text'] and 'section:1:requirements\nSecond' in sources[0]['text']


def test_question_keywords_do_not_remove_procedure_sections(monkeypatch):
    captured=[]
    def generate(request,evidence):
        captured.append(json.loads(a.build_messages(request,evidence)[1]['content']))
        return a.Generated(status='answered',answer='A supported answer. [s1]',source_ids=['s1']),'test'
    monkeypatch.setattr(a,'generate',generate)
    body='section:0:Trình tự thực hiện\nPROCESS\n\nsection:1:Cách thức thực hiện\nFEE\n\nsection:2:Thành phần hồ sơ\nREQUIREMENTS\n\nsection:4:Yêu cầu\nEXCEPTION'
    source=a.Source(id='primary',title='Procedure — primary — identity',url='https://example.test',text=body)
    for query in ['What is the fee?','Help me understand the next steps.']:
        response=a.chat(a.ChatRequest(message=query),retriever=lambda r:a.Retrieval(sources=[source]))
        actual=captured[-1]['retrieval']['sources'][0]['text']
        assert all(word in actual for word in ['PROCESS','FEE','REQUIREMENTS','EXCEPTION'])
        assert not response.documents
