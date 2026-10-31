"""Audit display-guide identity, quote coverage and quantities against source GETs."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import urlopen

EXPECTED = {'1.000771', '1.001146', '1.003326', '1.003342'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot-dir', type=Path)
    parser.add_argument('--api-base')
    args = parser.parse_args()
    if bool(args.snapshot_dir) == bool(args.api_base):
        parser.error('Choose one saved public snapshot directory or loopback API base.')
    if args.api_base:
        parsed = urlsplit(args.api_base)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            parser.error('Use an exact private loopback HTTP API origin.')

    def source(code, profile=False):
        if args.snapshot_dir:
            return json.loads((args.snapshot_dir / (code + ('-profile' if profile else '') + '.json')).read_text(encoding='utf-8'))
        with urlopen(args.api_base + '/procedures/' + code + ('/profile' if profile else ''), timeout=15) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
            assert len(payload) <= 8 * 1024 * 1024, 'Unexpected source response size'
            return json.loads(payload)

    def bilingual(value):
        assert isinstance(value, dict) and set(value) == {'en', 'vi'}
        assert all(isinstance(text, str) and text.strip() for text in value.values())

    def compact(value):
        return re.sub(r'\s+', '', value)

    artifact = json.loads((Path(__file__).resolve().parents[1] / 'docs/demo-guide-01-source-copy.json').read_text(encoding='utf-8'))
    assert artifact['schema_version'] == 'display-guide.v1'
    assert set(artifact['procedures']) == EXPECTED
    row_count = step_count = condition_count = 0
    for code, guide in artifact['procedures'].items():
        snapshot, profile = source(code), source(code, True)
        assert guide['procedure_code'] == code == snapshot['procedure_code']
        assert guide['source'] == dict(url=snapshot['source_url'], sha256=snapshot['sha256'], retrieved_at=snapshot['fetched_at'],
            snapshot_id=snapshot['id'], parser_version=snapshot['parser_version'], published_on=snapshot['published_on'], updated_on=snapshot['updated_on'])
        assert guide['profile'] == {key: profile[key] for key in ['id', 'run_id', 'baseline_id', 'output_sha256']}
        assert guide['evidence']['access'] == snapshot['analysis']['evidence_status']['access'] == 'source_attributed'
        bilingual(guide['title'])
        assert len(guide['checklist']) == len(snapshot['requirements'])
        for index, (row, original) in enumerate(zip(guide['checklist'], snapshot['requirements'], strict=True)):
            bilingual(row['title']); bilingual(row['text'])
            assert row['id'] == f'{code}:requirement:{original["id"]}'
            assert row['text']['vi'] == row['source_ref']['quote_vi'] == original['text_verbatim']
            assert row['source_ref']['json_pointer'] == f'/requirements/{index}'
            assert (row['originals'], row['copies']) == (original['originals'], original['copies'])
            assert row['kind'] == ('submission_instruction' if original['originals'] == original['copies'] == 0 else 'document')
            if row['condition'] is not None:
                bilingual(row['condition'])
            if 'nếu thuộc trường hợp cấp thị thực rời' in original['text_verbatim']:
                assert row['condition'] is not None, 'Separate-visa photo must stay conditional'
            row_count += 1
        for group, heading in [('steps', 'Trình tự thực hiện'), ('conditions', 'Yêu cầu, điều kiện thực hiện')]:
            index = next(i for i, section in enumerate(snapshot['document_json']['sections']) if section['heading'] == heading)
            original = snapshot['document_json']['sections'][index]['text_verbatim']
            quotes = []
            for row in guide[group]:
                bilingual(row['text'])
                assert row['text']['vi'] == row['source_ref']['quote_vi']
                assert row['source_ref']['json_pointer'] == f'/document_json/sections/{index}/text_verbatim'
                assert row['source_ref']['quote_vi'] in original
                quotes.append(row['source_ref']['quote_vi'])
            assert compact(''.join(quotes)) == compact(original), f'{code}: incomplete {group} source coverage'
        assert len(guide['steps']) == 3
        step_count += len(guide['steps']); condition_count += len(guide['conditions'])
        for note in guide['notes']:
            bilingual(note)
        if code != '1.001146':
            assert guide['installed_documents'] == []
    print(f'PASS: 4 source/profile identities; {row_count} exact requirement rows and quantities; '
          f'{step_count} full steps; {condition_count} full condition clauses; bilingual copy and form scope.')
    print('Structural/source audit only; translations remain working display copy, not official legal translations.')


if __name__ == '__main__':
    main()
