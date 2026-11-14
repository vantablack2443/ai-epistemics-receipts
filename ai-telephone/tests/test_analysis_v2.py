"""Hand-checked synthetic fixture, never research data."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from ai_telephone.analysis import load_jsonl, parse_generation_id, test_documents as documents_only, summary_rates, contrasts

FIXTURE = Path(__file__).parent / 'fixtures/v2'

def fixture_rows():
    docs = documents_only(load_jsonl(FIXTURE / 'sources.jsonl'))
    generations = load_jsonl(FIXTURE / 'results/terra/generations.jsonl')
    annotations = load_jsonl(FIXTURE / 'results/terra/ai-annotations.jsonl')
    return summary_rates(generations, annotations, docs)

def test_round_five_rates_and_paired_contrasts():
    rows = fixture_rows()
    rates = {(r['document_id'], r['prompt']):r['rate'] for r in rows}
    assert rates == {('T1','zero'):.5, ('T1','one'):1, ('T1','few'):1,
                     ('T2','zero'):0, ('T2','one'):None, ('T2','few'):.5}
    results = {r['contrast']:r for r in contrasts(rows, 'limited', 5)}
    assert tuple(results['few-zero'][k] for k in ('n_pairs','difference','low','high')) == (2,.5,.5,.5)
    assert (results['one-zero']['n_pairs'], results['one-zero']['difference']) == (1,.5)
    assert (results['few-one']['n_pairs'], results['few-one']['difference']) == (1,0)
    zero = [r for r in rows if r['prompt']=='zero']
    assert sum(r['n_unsupported'] for r in zero)/len(zero) == .5
    assert sum(r['labels']['strengthened'] for r in rows if r['prompt']=='few') == 1

def test_generation_ids_and_duplicate_annotation():
    assert parse_generation_id('long-07-few-limited-r3') == ('long-07','few','limited',3)
    assert parse_generation_id('dev-long-01-zero-free-r5') == ('dev-long-01','zero','free',5)
    anns = load_jsonl(FIXTURE/'results/terra/ai-annotations.jsonl')
    with pytest.raises(ValueError):
        summary_rates(load_jsonl(FIXTURE/'results/terra/generations.jsonl'), anns+[anns[0]], documents_only(load_jsonl(FIXTURE/'sources.jsonl')))
    gens = load_jsonl(FIXTURE/'results/terra/generations.jsonl')
    with pytest.raises(ValueError):
        summary_rates(gens+[gens[0]], anns, documents_only(load_jsonl(FIXTURE/'sources.jsonl')))

def test_cli_and_figures_from_fixtures(tmp_path):
    output = tmp_path/'analysis'
    subprocess.run([sys.executable,'-m','ai_telephone.analyze_cli','--results',str(FIXTURE/'results'),'--sources',str(FIXTURE/'sources.jsonl'),'--out',str(output)],check=True)
    with (output/'terra/failures.csv').open(newline='', encoding='utf-8') as f:
        assert list(csv.DictReader(f)) == [{'status':'timeout','count':'1'}]
    with (output/'terra/claims.csv').open(newline='', encoding='utf-8') as f:
        zero = next(r for r in csv.DictReader(f) if r['prompt']=='zero')
        assert int(zero['n_summaries']) == 2 and float(zero['mean_unsupported']) == .5
    with (output/'terra/errors.csv').open(newline='', encoding='utf-8') as f:
        strong = next(r for r in csv.DictReader(f) if r['prompt']=='few' and r['label']=='strengthened')
        assert int(strong['count']) == 1
    assert all('D1' not in line for line in (output/'terra/summary_rates.csv').read_text().splitlines())
    for name in ('summary_rates','contrasts','errors','claims','lengths','failures','by_drafter'):
        assert (output/'terra'/f'{name}.csv').exists()
    env = {**os.environ, 'MPLBACKEND':'Agg'}
    subprocess.run([sys.executable,'-m','ai_telephone.figures','--analysis',str(output),'--out',str(output/'figures')],check=True,env=env)
    for name in ('trajectory_terra','primary_contrasts','errors_terra','claims_terra','lengths_terra'):
        assert (output/'figures'/f'{name}.png').exists()
        assert (output/'figures'/f'{name}.svg').exists()
