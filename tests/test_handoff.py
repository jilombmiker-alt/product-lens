#!/usr/bin/env python3
"""Synthetic five-step contract regression. Does not execute skills, a model or a product."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/product-lens/scripts"))
from check_handoff import validate


def run(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    registry = {'schema_version': 1, 'project_id': 'fixture-only', 'artifact_registry': {}}
    docs = []
    # The material is explicitly invented: validates contracts, not product facts or real acceptance.
    chain = [('S04', 'H1', '截图只显示文字总结完成，导出入口可见；文件是否实际导出未知。'),
             ('B4', 'H2', '建议R01：用户可保存并导出总结。E01不证明原产品已导出；AC01检查实际文件。'),
             ('C7', 'H3', '替身代码产物：AC01本例未运行，本文仅作协议证据占位；不代表真实模型验证。'),
             ('F4', 'H5', '替身界面记录：无浏览器执行；保留导出失败分支和用户检查点。'),
             ('P7', 'H6', '替身发布记录：无云发布；版本/状态传递仅用于协议测试。')]
    for i, (stage, hid, text) in enumerate(chain, 1):
        aid = f'step-{i}'
        output = root / f'{aid}-artifact.md'
        output.write_text('# TEST FIXTURE ONLY\n' + text + '\n')
        feedback = root / f'{aid}-feedback.md'
        feedback.write_text('# SIMULATED USER FEEDBACK\n用于测试accepted分支；不是用户真实验收。版本1，范围fixture slice，环境simulation。\n')
        doc = {'schema_version': 1, 'record_kind': 'fixture', 'project_id': 'fixture-only',
               'artifact_id': aid, 'artifact_version': '1', 'mode': 'validation', 'stage': stage,
               'scope': 'fixture slice', 'environment': 'simulation',
               'upstream_refs': [{'artifact_id': f'step-{i-1}', 'version': '1'}] if i > 1 else [],
               'artifacts': [{'id': 'result', 'version': '1', 'path': output.name, 'sha256': digest(output)},
                             {'id': 'feedback', 'version': '1', 'path': feedback.name, 'sha256': digest(feedback)}],
               'checks': [{'id': 'local-check', 'required': True, 'status': 'passed', 'evidence_artifact_ids': ['result']}],
               'review_decision': 'pass',
               'human_review': {'required': True, 'checkpoint_id': hid, 'status': 'accepted',
                                'artifact_version': '1', 'scope': 'fixture slice', 'environment': 'simulation',
                                'source': {'kind': 'user_message', 'artifact_id': 'feedback', 'locator': 'fixture line 2'}},
               'allowed_uses': ['protocol_validation'], 'blocked_uses': ['product_or_cloud_completion_claim'],
               'next': {'stage': chain[i][0] if i < 5 else 'handoff', 'ready': True, 'blocker_ids': []},
               'payload': {'claim_id': 'E01', 'claim_level': 'unknown', 'original_product_export_verified': False}}
        path = root / f'{aid}.json'
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
        registry['artifact_registry'][aid] = {'version': '1', 'status': 'active', 'path': path.name, 'sha256': digest(path)}
        docs.append(doc)
    (root / 'run-card.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2))
    results = []
    def record(name, result, expected):
        actual = result['eligible_to_advance']
        results.append({'case': name, 'expected_eligible': expected, 'actual_eligible': actual,
                        'passed': actual is expected, 'errors': result['errors'], 'blockers': result['blockers']})
    for i, doc in enumerate(docs, 1):
        record('normal_chain_step_' + str(i), validate(doc, registry, root, True), True)
    def negative(name, mutate=None, reg_mutate=None, allow=True, base=0):
        doc = copy.deepcopy(docs[base]); reg = copy.deepcopy(registry)
        if mutate: mutate(doc)
        if reg_mutate: reg_mutate(reg)
        record(name, validate(doc, reg, root, allow), False)
    negative('fixture_refused_by_default', allow=False)
    negative('user_pending_blocks', lambda d: d['human_review'].update(status='pending'))
    negative('user_changes_requested_blocks', lambda d: d['human_review'].update(status='changes_requested'))
    negative('accepted_old_version_blocks', lambda d: d['human_review'].update(artifact_version='0'))
    negative('accepted_other_scope_blocks', lambda d: d['human_review'].update(scope='other'))
    negative('accepted_other_environment_blocks', lambda d: d['human_review'].update(environment='local'))
    negative('fake_acceptance_without_source_blocks', lambda d: d['human_review'].update(source=None))
    negative('ai_failed_user_accepted_blocks', lambda d: d['checks'][0].update(status='failed'))
    negative('required_pending_blocks', lambda d: d['checks'][0].update(status='pending'))
    negative('passed_without_evidence_blocks', lambda d: d['checks'][0].update(evidence_artifact_ids=[]))
    negative('missing_evidence_reference_blocks', lambda d: d['checks'][0].update(evidence_artifact_ids=['absent']))
    negative('na_without_reason_blocks', lambda d: d['checks'][0].update(status='not_applicable', reason=''))
    negative('upstream_retracted_blocks', reg_mutate=lambda rg: rg['artifact_registry']['step-1'].update(status='retracted'), base=4)
    negative('upstream_new_version_blocks', reg_mutate=lambda rg: rg['artifact_registry']['step-1'].update(version='2'), base=4)
    negative('file_hash_mismatch_blocks', lambda d: d['artifacts'][0].update(sha256='0'*64))
    negative('missing_file_blocks', lambda d: d['artifacts'][0].update(path='missing.md'))
    negative('path_escape_blocks', lambda d: d['artifacts'][0].update(path='../outside.txt'))
    negative('required_human_gate_cannot_be_disabled', lambda d: d['human_review'].update(required=False, status='not_required'))
    negative('project_cannot_consume_fixture', lambda d: d.update(record_kind='project'), base=4)
    negative('missing_schema_blocks', lambda d: d.pop('schema_version'))
    negative('wrong_project_blocks', lambda d: d.update(project_id='other'))
    doc=copy.deepcopy(docs[0]); doc['checks'].append({'id':'optional','required':False,'status':'pending','evidence_artifact_ids':[]})
    doc['review_decision']='conditional_pass'
    record('optional_pending_allows_declared_limited_scope',validate(doc,registry,root,True),True)
    reg=copy.deepcopy(registry);reg['artifact_registry']['unrelated']={'version':'2','status':'retracted'}
    record('unrelated_change_does_not_block',validate(docs[4],reg,root,True),True)
    negative('unproven_user_review_override_blocks', lambda d: d['human_review'].update(required=False,status='not_required'),
             reg_mutate=lambda rg: rg.update(review_overrides={'S04':{'required':False}}))
    doc=copy.deepcopy(docs[0]);doc['human_review'].update(required=False,status='not_required')
    reg=copy.deepcopy(registry);feedback=doc['artifacts'][1]
    reg['review_overrides']={'S04':{'required':False,'artifact_version':'1','scope':'fixture slice','environment':'simulation',
                                   'reason':'Synthetic instruction override test, not actual waiver',
                                   'source':{'kind':'user_message','path':feedback['path'],'sha256':feedback['sha256'],'locator':'fixture line 2'}}}
    record('bound_explicit_override_supported',validate(doc,reg,root,True),True)
    negative('declared_blockers_prevent_eligibility_even_when_paused', lambda d: d['next'].update(ready=False,blocker_ids=['unresolved-review']))
    negative('empty_allowed_use_blocks', lambda d: d.update(allowed_uses=['']))
    negative('whitespace_allowed_use_blocks', lambda d: d.update(allowed_uses=['  ']))
    negative('non_string_allowed_use_blocks', lambda d: d.update(allowed_uses=[False]))
    negative('contradictory_allowed_and_blocked_use', lambda d: d.update(allowed_uses=['publish'],blocked_uses=['publish']))
    negative('whitespace_normalized_use_conflict', lambda d: d.update(allowed_uses=['publish '],blocked_uses=[' publish']))
    negative('blank_declared_blocker_invalid', lambda d: d['next'].update(ready=False,blocker_ids=['']))
    doc=copy.deepcopy(docs[0]);doc['next']['ready']=False
    result=validate(doc,registry,root,True)
    record('explicit_pause_without_blockers_keeps_eligibility_but_not_ready',result,True)
    assert result['declared_ready'] is False
    # Reload persisted records: demonstrates file-based resume, not an independent model session.
    saved=json.loads((root/'step-5.json').read_text());saved_reg=json.loads((root/'run-card.json').read_text())
    record('persisted_chain_resume',validate(saved,saved_reg,root,True),True)
    # Modify upstream feedback and digest to prove recursion checks gates, not just hashes.
    first=copy.deepcopy(docs[0]);first['human_review']['status']='pending';first['next']['ready']=False
    (root/'step-1.json').write_text(json.dumps(first));saved_reg['artifact_registry']['step-1']['sha256']=digest(root/'step-1.json')
    record('downstream_cannot_skip_upstream_user_review',validate(saved,saved_reg,root,True),False)
    # Restore fixture baseline for a reproducible retained walkthrough.
    (root/'step-1.json').write_text(json.dumps(docs[0],ensure_ascii=False,indent=2))
    report={'scope':'synthetic_handoff_protocol_regression','status':'pass' if all(x['passed'] for x in results) else 'fail',
            'cases':results,'counts':{'total':len(results),'passed':sum(x['passed'] for x in results)},
            'not_proven':['skill自主执行','真实用户确认','OiiOii页面事实','代码/模型/浏览器/部署效果','语义证据正确性'],
            'note':'All feedback and artifacts are marked fixtures. Accepted fields only exercise the gate; they are not real approvals.'}
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',help='Save report to this path')
    parser.add_argument('--retain-fixtures',help='Create a NEW directory for inspectable synthetic inputs')
    args=parser.parse_args()
    if args.retain_fixtures:
        dest=Path(args.retain_fixtures)
        if dest.exists():
            parser.error('fixture directory must not already exist')
        report=run(dest)
    else:
        with tempfile.TemporaryDirectory(prefix='sop-handoff-test-') as tmp:
            report=run(tmp)
    if args.output:
        Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scope':report['scope'],'status':report['status'],**report['counts']},ensure_ascii=False))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
