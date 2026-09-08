#!/usr/bin/env python3
"""Read-only SOP handoff checks. Structural consistency is not semantic or user acceptance."""
import argparse
import hashlib
import json
from pathlib import Path


def validate(doc, registry, root, allow_fixtures=False, stack=()):
    root = Path(root).resolve()
    errors, blockers = [], []
    def err(message):
        errors.append(message)
    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())
    def safe_file(value):
        if not nonempty(value):
            return None
        candidate = (root / value).resolve()
        if Path(value).is_absolute() or not candidate.is_relative_to(root) or not candidate.is_file():
            return None
        return candidate
    def finish():
        derived = not errors and not blockers
        declared = doc.get('next', {}).get('ready') if isinstance(doc, dict) and isinstance(doc.get('next'), dict) else None
        if declared is True and not derived:
            errors.append('next.ready=true contradicts evidence or gates')
        # A deliberate pause is allowed even if all technical prerequisites pass.
        return {'valid': not errors, 'eligible_to_advance': not errors and not blockers,
                'declared_ready': declared, 'errors': errors, 'blockers': blockers,
                'limits': 'Only structure, files, digests and declared gates checked; user intent, source truth, semantic quality and operation authorization need review.'}
    if not isinstance(doc, dict) or not isinstance(registry, dict):
        err('handoff and registry must be objects')
        return finish()
    if type(doc.get('schema_version')) is not int or doc.get('schema_version') != 1 or type(registry.get('schema_version')) is not int or registry.get('schema_version') != 1:
        err('schema_version must be 1')
    kind = doc.get('record_kind')
    if kind not in ('project', 'fixture'):
        err('record_kind must be project; templates cannot pass')
    if kind == 'fixture' and not allow_fixtures:
        err('fixture rejected without --allow-fixtures')
    for key in ('project_id', 'artifact_id', 'artifact_version', 'mode', 'stage', 'scope', 'environment'):
        if not nonempty(doc.get(key)):
            err(key + ' must be a nonempty string')
    if doc.get('project_id') != registry.get('project_id'):
        err('project_id mismatch')
    ident = doc.get('artifact_id')
    if ident in stack or len(stack) >= 100:
        err('upstream cycle or dependency depth limit')
        return finish()
    next_stack = (*stack, ident)
    arrays = ('upstream_refs', 'artifacts', 'checks', 'allowed_uses', 'blocked_uses')
    for key in arrays:
        if not isinstance(doc.get(key), list):
            err(key + ' must be an array')
    if errors:
        return finish()
    for key in ('allowed_uses', 'blocked_uses'):
        if any(not nonempty(value) for value in doc[key]):
            err(key + ' must contain nonempty strings')
    allowed = {v.strip() for v in doc['allowed_uses'] if nonempty(v)}
    blocked = {v.strip() for v in doc['blocked_uses'] if nonempty(v)}
    if allowed & blocked:
        err('same use cannot be both allowed and blocked')
    if not doc['artifacts'] or not doc['checks']:
        err('at least one artifact and one actual check are required')
    artifacts = {}
    for item in doc['artifacts']:
        if not isinstance(item, dict):
            err('artifact must be an object')
            continue
        aid = item.get('id')
        if not nonempty(aid) or aid in artifacts:
            err('missing or duplicate artifact id')
            continue
        artifacts[aid] = item
        file = safe_file(item.get('path'))
        if file is None:
            err('artifact path missing or outside root: ' + aid)
        elif item.get('sha256') != hashlib.sha256(file.read_bytes()).hexdigest():
            err('artifact digest mismatch: ' + aid)
        if not nonempty(item.get('version')):
            err('artifact version missing: ' + aid)
    seen = set()
    for check in doc['checks']:
        if not isinstance(check, dict):
            err('check must be an object')
            continue
        cid = check.get('id')
        if not nonempty(cid) or cid in seen:
            err('missing or duplicate check id')
        else:
            seen.add(cid)
        if not isinstance(check.get('required'), bool):
            err('check.required must be boolean')
        status = check.get('status')
        if status not in ('passed', 'failed', 'pending', 'not_applicable'):
            err('invalid check status: ' + str(cid))
        evidence = check.get('evidence_artifact_ids', [])
        if not isinstance(evidence, list) or any(not isinstance(e, str) or e not in artifacts for e in evidence):
            err('check evidence reference missing: ' + str(cid))
        elif status == 'passed' and not evidence:
            err('passed check requires evidence: ' + str(cid))
        if status == 'not_applicable' and not nonempty(check.get('reason')):
            err('not_applicable needs a reason: ' + str(cid))
        if check.get('required') and status not in ('passed', 'not_applicable'):
            blockers.append('required check not passed: ' + str(cid))
    entries = registry.get('artifact_registry')
    if not isinstance(entries, dict):
        err('registry.artifact_registry must be object')
        entries = {}
    own = entries.get(ident)
    if isinstance(own, dict) and (own.get('status') != 'active' or own.get('version') != doc.get('artifact_version')):
        blockers.append('current handoff inactive or stale in registry')
    for upstream in doc['upstream_refs']:
        if not isinstance(upstream, dict) or not nonempty(upstream.get('artifact_id')):
            err('invalid upstream reference')
            continue
        uid = upstream['artifact_id']
        entry = entries.get(uid)
        if not isinstance(entry, dict):
            err('upstream missing in registry: ' + uid)
            continue
        if entry.get('status') != 'active' or entry.get('version') != upstream.get('version'):
            blockers.append('upstream inactive or stale: ' + uid)
            continue
        path = safe_file(entry.get('path'))
        if path is None:
            err('upstream handoff missing or outside root: ' + uid)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry.get('sha256'):
            err('upstream handoff digest mismatch: ' + uid)
            continue
        try:
            prior = json.loads(path.read_text())
        except (OSError, ValueError):
            err('upstream handoff unreadable: ' + uid)
            continue
        if not isinstance(prior, dict) or prior.get('artifact_id') != uid or prior.get('artifact_version') != entry.get('version'):
            err('upstream identity/version mismatch: ' + uid)
            continue
        if kind == 'project' and prior.get('record_kind') != 'project':
            err('project cannot consume fixture: ' + uid)
            continue
        result = validate(prior, registry, root, allow_fixtures, next_stack)
        if not result['eligible_to_advance'] or result['declared_ready'] is not True:
            blockers.append('upstream not released for dependent use: ' + uid)
    decision = doc.get('review_decision')
    if decision not in ('pass', 'conditional_pass', 'return_for_revision'):
        err('invalid review_decision')
    elif decision == 'return_for_revision':
        blockers.append('review returned for revision')
    if decision == 'conditional_pass' and (not doc['allowed_uses'] or not doc['blocked_uses']):
        err('conditional_pass requires explicit allowed and blocked uses')
    human = doc.get('human_review')
    if not isinstance(human, dict) or not isinstance(human.get('required'), bool):
        err('human_review and boolean required must be explicit')
    else:
        default_checkpoints = {'S04': 'H1', 'B4': 'H2', 'C7': 'H3', 'F1': 'H4', 'F4': 'H5', 'P7': 'H6'}
        checkpoint = default_checkpoints.get(doc.get('stage'))
        override = registry.get('review_overrides', {}).get(doc.get('stage')) if isinstance(registry.get('review_overrides', {}), dict) else None
        waived = False
        if override is not None:
            source = override.get('source') if isinstance(override, dict) else None
            proof = safe_file(source.get('path')) if isinstance(source, dict) else None
            waived = (isinstance(override, dict) and override.get('required') is False
                      and override.get('artifact_version') == doc.get('artifact_version')
                      and override.get('scope') == doc.get('scope') and override.get('environment') == doc.get('environment')
                      and proof is not None and source.get('kind') == 'user_message'
                      and source.get('sha256') == hashlib.sha256(proof.read_bytes()).hexdigest()
                      and nonempty(source.get('locator')) and nonempty(override.get('reason')))
            if not waived:
                err('review override lacks bound user instruction evidence')
        if checkpoint and not waived and (human.get('required') is not True or human.get('checkpoint_id') != checkpoint):
            err('default checkpoint cannot be silently bypassed: ' + checkpoint)
        status = human.get('status')
        if status not in ('pending', 'accepted', 'changes_requested', 'not_required'):
            err('invalid human_review.status')
        if human['required'] and not nonempty(human.get('checkpoint_id')):
            err('required human review needs checkpoint id')
        if human['required'] and status != 'accepted':
            blockers.append('user review required and not accepted')
        if status == 'changes_requested':
            blockers.append('user requested changes')
        if status == 'accepted':
            for key in ('artifact_version', 'scope', 'environment'):
                if human.get(key) != doc.get(key):
                    err('user acceptance binding mismatch: ' + key)
            source = human.get('source')
            if not isinstance(source, dict) or source.get('kind') != 'user_message' or not isinstance(source.get('artifact_id'), str) or source.get('artifact_id') not in artifacts or not nonempty(source.get('locator')):
                err('accepted requires traceable user feedback source')
    nxt = doc.get('next')
    if not isinstance(nxt, dict) or not isinstance(nxt.get('ready'), bool) or not isinstance(nxt.get('blocker_ids'), list):
        err('next.ready and next.blocker_ids must be explicit')
    else:
        if any(not nonempty(value) for value in nxt['blocker_ids']):
            err('next.blocker_ids must contain nonempty strings')
        if nxt['blocker_ids']:
            blockers.append('next contains unresolved blocker ids')
        if nxt['ready'] and (not nonempty(nxt.get('stage')) or not allowed):
            err('ready requires next stage and allowed uses')
    if not isinstance(doc.get('payload'), dict):
        err('payload must be object')
    return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('handoff')
    parser.add_argument('--registry', required=True)
    parser.add_argument('--root', default='.')
    parser.add_argument('--allow-fixtures', action='store_true')
    args = parser.parse_args()
    try:
        doc = json.loads(Path(args.handoff).read_text())
        registry = json.loads(Path(args.registry).read_text())
        result = validate(doc, registry, args.root, args.allow_fixtures)
    except (OSError, ValueError) as exc:
        result = {'valid': False, 'eligible_to_advance': False, 'errors': [type(exc).__name__ + ': input could not be read or parsed'], 'blockers': []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['eligible_to_advance'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
