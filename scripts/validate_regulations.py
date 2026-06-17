#!/usr/bin/env python3
"""Validate the regulatory-layer YAML data (data/regulations, controls, mappings).

Checks each file against a JSON schema, then verifies referential integrity:
mappings must reference controls that exist and obligation refs that exist in the
named regulation. Run in CI and before seeding.

Usage:
    python3 scripts/validate_regulations.py [data_dir]
Exit code 0 if valid, 1 if any errors.
"""
import os
import sys
import yaml
from jsonschema import Draft7Validator

# Allow running as `python3 scripts/validate_regulations.py` from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Enums kept in sync with the models (single source of truth).
from app.models.regulation import (  # noqa: E402
    REGULATION_STATUSES, REFERENCE_FRAMEWORKS, CONTROL_DOMAINS,
)


_OBLIGATION_SCHEMA = {
    'type': 'object',
    'required': ['ref', 'title'],
    'additionalProperties': False,
    'properties': {
        'ref': {'type': 'string'},
        'title': {'type': 'string'},
        'text': {'type': 'string'},
        'children': {'type': 'array', 'items': {'$ref': '#/definitions/obligation'}},
    },
}

REGULATION_SCHEMA = {
    'type': 'object',
    'definitions': {'obligation': _OBLIGATION_SCHEMA},
    'required': ['regulation'],
    'additionalProperties': False,
    'properties': {
        'regulation': {
            'type': 'object',
            'required': ['name', 'slug'],
            'additionalProperties': False,
            'properties': {
                'name': {'type': 'string'},
                'short_code': {'type': 'string'},
                'slug': {'type': 'string'},
                'version': {'type': 'string'},
                'status': {'enum': REGULATION_STATUSES},
                'effective_date': {'type': 'string'},
                'source_url': {'type': 'string'},
                'description': {'type': 'string'},
            },
        },
        'obligations': {'type': 'array', 'items': {'$ref': '#/definitions/obligation'}},
    },
}

CONTROLS_SCHEMA = {
    'type': 'object',
    'required': ['controls'],
    'additionalProperties': False,
    'properties': {
        'controls': {
            'type': 'array',
            'items': {
                'type': 'object',
                'required': ['code', 'title'],
                'additionalProperties': False,
                'properties': {
                    'code': {'type': 'string'},
                    'title': {'type': 'string'},
                    'domain': {'enum': CONTROL_DOMAINS},
                    'description': {'type': 'string'},
                    'guidance': {'type': 'string'},
                    'checks': {'type': 'array', 'items': {'type': 'string'}},
                    'evidence_requirements': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'required': ['title'],
                            'additionalProperties': False,
                            'properties': {
                                'title': {'type': 'string'},
                                'description': {'type': 'string'},
                                'type': {'type': 'string'},
                                'cadence_days': {'type': 'integer'},
                            },
                        },
                    },
                    'references': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'required': ['framework'],
                            'additionalProperties': False,
                            'properties': {
                                'framework': {'enum': REFERENCE_FRAMEWORKS},
                                'ref_code': {'type': 'string'},
                                'title': {'type': 'string'},
                            },
                        },
                    },
                },
            },
        },
    },
}

MAPPINGS_SCHEMA = {
    'type': 'object',
    'required': ['regulation_slug', 'mappings'],
    'additionalProperties': False,
    'properties': {
        'regulation_slug': {'type': 'string'},
        'mappings': {
            'type': 'array',
            'items': {
                'type': 'object',
                'required': ['control'],
                'additionalProperties': False,
                'properties': {
                    'control': {'type': 'string'},
                    'obligations': {'type': 'array', 'items': {'type': 'string'}},
                },
            },
        },
    },
}


def _load(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def _schema_errors(filepath, data, schema):
    label = os.path.relpath(filepath)
    errors = []
    for err in sorted(Draft7Validator(schema).iter_errors(data), key=str):
        path = '/'.join(str(p) for p in err.path) or '(root)'
        errors.append(f'{label}: {path}: {err.message}')
    return errors


def _collect_obligation_refs(obligations, acc):
    for ob in obligations or []:
        acc.add(ob.get('ref'))
        _collect_obligation_refs(ob.get('children'), acc)


def validate_data_dir(data_dir):
    """Return a list of human-readable error strings ([] means valid)."""
    errors = []

    control_codes = set()
    obligation_refs = {}  # slug -> set(refs)

    # --- regulations ---
    reg_dir = os.path.join(data_dir, 'regulations')
    if os.path.isdir(reg_dir):
        for slug in sorted(os.listdir(reg_dir)):
            filepath = os.path.join(reg_dir, slug, 'regulation.yaml')
            if not os.path.exists(filepath):
                continue
            data = _load(filepath)
            errors.extend(_schema_errors(filepath, data, REGULATION_SCHEMA))
            if isinstance(data, dict):
                reg_slug = (data.get('regulation') or {}).get('slug')
                refs = set()
                _collect_obligation_refs(data.get('obligations'), refs)
                if reg_slug:
                    obligation_refs[reg_slug] = refs

    # --- controls ---
    controls_dir = os.path.join(data_dir, 'controls')
    if os.path.isdir(controls_dir):
        for filename in sorted(os.listdir(controls_dir)):
            if not filename.endswith(('.yaml', '.yml')):
                continue
            filepath = os.path.join(controls_dir, filename)
            data = _load(filepath)
            errors.extend(_schema_errors(filepath, data, CONTROLS_SCHEMA))
            if isinstance(data, dict):
                for c in data.get('controls', []):
                    if isinstance(c, dict) and c.get('code'):
                        control_codes.add(c['code'])

    # --- mappings (+ referential integrity) ---
    mappings_dir = os.path.join(data_dir, 'mappings')
    if os.path.isdir(mappings_dir):
        for filename in sorted(os.listdir(mappings_dir)):
            if not filename.endswith(('.yaml', '.yml')):
                continue
            filepath = os.path.join(mappings_dir, filename)
            label = os.path.relpath(filepath)
            data = _load(filepath)
            errors.extend(_schema_errors(filepath, data, MAPPINGS_SCHEMA))
            if not isinstance(data, dict):
                continue
            slug = data.get('regulation_slug')
            known_refs = obligation_refs.get(slug, set())
            for mapping in data.get('mappings', []):
                if not isinstance(mapping, dict):
                    continue
                code = mapping.get('control')
                if code and code not in control_codes:
                    errors.append(f'{label}: mapping references unknown control {code}')
                for ref in mapping.get('obligations', []):
                    if ref not in known_refs:
                        errors.append(
                            f'{label}: mapping references unknown obligation {ref} '
                            f'for regulation {slug}')

    return errors


def main(argv):
    data_dir = argv[1] if len(argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    errors = validate_data_dir(data_dir)
    if errors:
        print(f'FAIL: {len(errors)} validation error(s) in {data_dir}:')
        for e in errors:
            print(f'  - {e}')
        return 1
    print(f'OK: regulatory data in {data_dir} is valid.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
