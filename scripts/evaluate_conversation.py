"""Live regression of clarification follow-ups and general/citizen questions.

Uses configured services and public procedure evidence, never applicant values.
Run: python -m scripts.evaluate_conversation --output output/conversation-eval.json
Read the recorded answers: structural checks are not semantic verification.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from api.assistant import ChatRequest, Turn, chat, retrieve
from api.assistant_policy import POLICY_VERSION
from api.rag import members, question, read_state, release_info, sign_state


def evaluate(request, label):
    try:
        response=chat(request,retriever=retrieve)
        return dict(case=label,request=request.model_dump(exclude={'retrieval_state'}),
                    response=response.model_dump(mode='json',exclude={'retrieval_state'})),response
    except HTTPException as exc:
        return dict(case=label,http_status=exc.status_code,error=exc.detail),None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    cases=[('general-copy',ChatRequest(message='What is the difference between an original document and a certified copy?')),
           ('missing-fee',ChatRequest(message='Exactly how much will my application cost?')),
           ('marriage-documents',ChatRequest(message='We want to get married. What paperwork should we prepare?',procedure_code='1.000894')),
           ('residence-documents',ChatRequest(message='Tôi muốn đăng ký tạm trú. Cần chuẩn bị giấy tờ gì?',procedure_code='1.004194')),
           ('business-overview',ChatRequest(message='I want to register a small household business. Help me understand the next steps.',procedure_code='1.001612')),
           ('unrelated',ChatRequest(message='Write a Python game for me.'))]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda pair:evaluate(pair[1],pair[0])[0],cases))
    release=str(release_info()['id'])
    candidates=members(release,['1.001146','1.003326'])
    state=sign_state(dict(release=release,codes=[m['code'] for m in candidates],asked=[],
        query='I want to extend my stay. Help me with the next steps.',question=question(candidates,[])))
    history=[]
    for message in ["I'm not sure",'whats the difference between these two?',
                    'What do you mean by sponsor?']:
        row,response=evaluate(ChatRequest(message=message,retrieval_state=state,history=history),'clarification-followup')
        if response:
            row['pending_codes']=read_state(response.retrieval_state)['codes']
            state=response.retrieval_state
            history.extend([Turn(role='user',content=message),Turn(role='assistant',content=response.answer)])
        results.append(row)
    report=dict(policy_version=POLICY_VERSION,created_at=datetime.now(timezone.utc).isoformat(),
        results=results,semantic_review='pending')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    for row in results:
        response=row.get('response',{})
        print(json.dumps(dict(case=row['case'],status=response.get('status'),model=response.get('model'),
            citations=len(response.get('citations',[])),documents=len(response.get('documents',[])),error=row.get('error'))),flush=True)
    if any('error' in row for row in results): raise SystemExit(1)


if __name__=='__main__':main()
