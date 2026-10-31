"""Run the reusable visual mapper on NA5; retain its output for review."""
import argparse
import json
from api.config import ROOT
from api.field_mapping import map_form
from api.storage import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['openai','codex'], default=None)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--pdf', help='Analyse a new rendering without replacing the active draft yet')
    args = parser.parse_args()
    spec = json.loads((ROOT/'data/forms/NA5/workflow.json').read_text(encoding='utf-8'))
    context = (ROOT/'data/procedures/1.001146/procedure.json').read_text(encoding='utf-8')
    # Supply full captured sections, not internal provenance or obsolete field guesses.
    context = json.dumps(json.loads(context)['document_json'], ensure_ascii=False)
    result = map_form(ROOT/args.pdf if args.pdf else ROOT/spec['pdf_path'], spec['form_sha256'], context=context,
                      hints=[dict(id=f['id'],label=f['label']) for f in spec['fields']],
                      force=args.force, provider=args.provider)
    write_json(ROOT/'data/forms/NA5/model-run.json', result)
    print(json.dumps(dict(fields=len(result['fields']), issues=result['result']['issues'], metadata=result['metadata'], cache=result['cache_path']), ensure_ascii=True))


if __name__ == '__main__':
    main()
