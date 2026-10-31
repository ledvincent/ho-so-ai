"""Live HTTP demo checks with public questions and fictional form values only."""
import argparse
import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pymupdf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8001')
    parser.add_argument('--output',type=Path,default=Path('output/assistant-demo'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    report=dict(created_at=datetime.now(timezone.utc).isoformat(),base_url=args.base_url,
                mocked=False,cases=[],note='Development checks plus manual answer review, not a general accuracy guarantee.')
    with httpx.Client(base_url=args.base_url,timeout=180) as client:
        def chat(name,message,code='1.001146',**kwargs):
            request=dict(message=message,history=[],**kwargs)
            if code:request['procedure_code']=code
            response=client.post('/assistant/chat',json=request)
            body=response.json()
            item=dict(name=name,question=message,http_status=response.status_code,
                      response={k:v for k,v in body.items() if k!='retrieval_state'})
            report['cases'].append(item)
            assert response.status_code==200
            citations={c['id'] for c in body['citations']}
            assert set(re.findall(r'\[([^\[\]\n]+)\]',body['answer']))<=citations
            assert all(set(d['source_ids'])<=citations for d in body['documents'])
            return body

        def run(name,operation):
            before=len(report['cases'])
            print(name+': RUN',flush=True)
            try:
                detail=operation()
                if len(report['cases'])==before:report['cases'].append(dict(name=name,detail=detail))
                report['cases'][-1]['passed']=True
            except Exception as exc:
                if len(report['cases'])==before:report['cases'].append(dict(name=name))
                report['cases'][-1].update(passed=False,error_type=type(exc).__name__)
            print(name+': '+('PASS' if report['cases'][-1]['passed'] else 'FAIL'),flush=True)

        def documents(vi=False):
            body=chat('documents_vi' if vi else 'documents_en',
                'Tôi chưa hiểu cần chuẩn bị giấy tờ gì và điền mẫu đơn ra sao. Hướng dẫn tôi với.' if vi else
                "I'm confused about the paperwork. Can you walk me through what I need and help me with the form?")
            assert body['status'] in ('answered','insufficient_context')
            form=next(d['form'] for d in body['documents'] if d['form'])
            assert form['form_id']=='NA5' and form['procedure_code']=='1.001146'
            actual=client.get(form['schema_url']).json()
            assert actual['template_version']==form['template_version']
            assert actual['download_available']==form['download_available'] is False
            assert any(d['requirement']=='conditional' and d['condition'] for d in body['documents'])
            assert not any(d['title']=='One complete set' and d['kind']!='submission_instruction' for d in body['documents'])
            assert not any('photo' in d['title'].lower() and d['requirement']=='required' for d in body['documents'])
            assert body['model']=='gpt-6.1-sol'
            if vi:assert re.search(r'hộ chiếu|giấy tờ|hồ sơ',body['answer'],re.I) and any(d['title']=='Tờ khai NA5' for d in body['documents'])
            else:
                visible=body['answer']+' '+json.dumps(body['documents'],ensure_ascii=False)+' '+json.dumps(body['citations'],ensure_ascii=False)
                assert not re.search(r'[ăâđêôơưĂÂĐÊÔƠƯ\u1ea0-\u1ef9]',visible)
            return body
        run('documents_en',documents)
        run('documents_vi',lambda:documents(True))

        def duration():
            body=chat('processing_en','How long does this procedure take?')
            assert body['status']=='answered' and re.search(r'5\s+working\s+days',body['answer'],re.I)
            assert body['citations'] and body['model']=='gpt-6.1-sol'
        run('processing_en',duration)

        def duration_vi():
            body=chat('processing_vi','Thủ tục này mất bao lâu?')
            assert body['status']=='answered' and 'ngày làm việc' in body['answer'] and body['citations']
        run('processing_vi',duration_vi)

        def fee():
            body=chat('fee_conflict','How much is the fee?')
            assert body['status']=='insufficient_context' and len(body['citations'])>=2
            assert '10' in body['answer'] and re.search(r'no fee|no charge|not.*fee|not charged|free|not specified',body['answer'],re.I)
        run('fee_conflict',fee)

        def photo():
            body=chat('photo','Do I have to upload a photo here to extend my stay?')
            assert body['status'] in ('answered','insufficient_context') and re.search(r'no|not|don.t',body['answer'],re.I)
            assert not body['documents']
        run('photo',photo)

        def clarify():
            body=chat('ambiguous_procedure','NA5',code=None)
            assert body['status']=='needs_clarification' and len(body['choices'])>1 and body['retrieval_state']
            assert body['documents']==[]
        run('ambiguous_procedure',clarify)

        def broad():
            body=chat('broad_start','I want to stay in Vietnam longer. What should I do?',code=None)
            assert body['status']=='needs_clarification' and body['choices']
            assert len(body['answer'].split())>20 and not body['documents']
        run('broad_start',broad)

        def scope():
            body=chat('scope','Write a Python stock-trading bot unrelated to this procedure.')
            assert body['status']=='out_of_scope' and not body['citations'] and not body['documents']
        run('scope',scope)

        def form_flow():
            route='/documents/na5-provincial-stay-extension'
            schema=client.get(route+'/schema').json()
            partial=client.post(route+'/validate',json={'values':{'applicant_full_name':'Fictional Tester'},'template_version':schema['template_version']})
            assert partial.status_code==200 and partial.json()['missing_fields'] and not partial.json()['ready_for_preview']
            assert partial.json()['values']['passport_number']==''
            example=client.get(route+'/example').json()
            assert example['fictional'] is True
            request=dict(values=example['values'],template_version=schema['template_version'])
            assert client.post(route+'/validate',json=request).json()['ready_for_preview']
            pdf=client.post(route+'/preview',json=request)
            assert pdf.status_code==200 and pdf.headers['content-type']=='application/pdf'
            with pymupdf.open(stream=pdf.content,filetype='pdf') as rendered:
                assert len(rendered)==3 and 'ÉLODIE EXEMPLE' in rendered[0].get_text()
                assert 'TEMPLATE REVIEW DRAFT' in rendered[0].get_text()
            (args.output/'fictional-na5-preview.pdf').write_bytes(pdf.content)
            pages=client.post(route+'/preview-pages',json=request)
            assert pages.status_code==200 and pages.headers['X-Review-Token']
            images=pages.json()['pages']
            assert len(images)==3
            for page in images:
                raw=base64.b64decode(page['image_data_url'].split(',',1)[1])
                assert raw.startswith(b'\x89PNG')
                (args.output/f"fictional-na5-page-{page['page_number']}.png").write_bytes(raw)
            blocked=client.post(route+'/download',json={**request,'review_token':pages.headers['X-Review-Token'],'confirmed':True})
            assert blocked.status_code==409
            changed=client.post(route+'/validate',json={**request,'template_version':'0'*64})
            assert changed.status_code==409
            invalid=client.post(route+'/validate',json={'values':{'birth_date':'2026-02-31'}})
            assert invalid.status_code==422
            return dict(preview_http=200,pages=3,download_http=409,stale_template_http=409,invalid_date_http=422,applicant_values_sent_to_chat=False)
        run('form_flow',form_flow)

    report['passed']=all(c['passed'] for c in report['cases'])
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Report:',args.output/'report.json')
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
