"""Tests for the regulatory-layer YAML seed loader (Phase 1)."""
import textwrap

from app.models import Regulation, Obligation, Control
from app.utils.seed import (
    seed_regulation_file, seed_controls_file, seed_mappings_file,
)


def _write(path, content):
    path.write_text(textwrap.dedent(content))
    return str(path)


def test_seed_regulation_file_builds_obligation_tree(db_session, tmp_path):
    fp = _write(tmp_path / 'regulation.yaml', """
        regulation:
          short_code: NIS2
          name: "NIS2 Directive"
          slug: nis2
          version: "2022/2555"
          status: in_force
          source_url: "https://example.eu/nis2"
        obligations:
          - ref: "Art.21"
            title: "Risk-management measures"
            children:
              - ref: "Art.21(2)(d)"
                title: "Supply chain security"
                text: "Security in acquisition, development, maintenance."
    """)
    seed_regulation_file(fp)

    reg = Regulation.query.filter_by(slug='nis2').one()
    assert reg.status == 'in_force'
    assert reg.obligations.count() == 2
    child = Obligation.query.filter_by(regulation_id=reg.id, ref='Art.21(2)(d)').one()
    assert child.parent.ref == 'Art.21'
    assert child.content_hash  # sha256 computed for delta detection


def test_seed_controls_file_links_checks_refs_and_requirements(db_session, seed_data, tmp_path):
    # seed_data provides checks with check_number '1.1', '1.2', '1.3'
    fp = _write(tmp_path / 'controls.yaml', """
        controls:
          - code: SC-01
            title: "Supply-chain risk management"
            domain: SupplyChain
            checks: ["1.1", "1.2"]
            evidence_requirements:
              - title: "Approved supplier register"
                type: document
                cadence_days: 365
            references:
              - {framework: ISO27001, ref_code: "A.5.19", title: "Supplier relationships"}
    """)
    seed_controls_file(fp)

    control = Control.query.filter_by(code='SC-01').one()
    assert {c.check_number for c in control.checks} == {'1.1', '1.2'}
    assert control.evidence_requirements[0].cadence_days == 365
    assert control.references[0].framework == 'ISO27001'


def test_seed_mappings_file_links_control_to_obligation(db_session, tmp_path):
    reg_fp = _write(tmp_path / 'regulation.yaml', """
        regulation: {short_code: NIS2, name: "NIS2", slug: nis2, status: in_force}
        obligations:
          - ref: "Art.21(2)(d)"
            title: "Supply chain"
    """)
    ctrl_fp = _write(tmp_path / 'controls.yaml', """
        controls:
          - {code: SC-01, title: "Supply-chain RM", domain: SupplyChain}
    """)
    map_fp = _write(tmp_path / 'mappings.yaml', """
        regulation_slug: nis2
        mappings:
          - control: SC-01
            obligations: ["Art.21(2)(d)"]
    """)
    seed_regulation_file(reg_fp)
    seed_controls_file(ctrl_fp)
    seed_mappings_file(map_fp)

    control = Control.query.filter_by(code='SC-01').one()
    assert control.obligations[0].ref == 'Art.21(2)(d)'


def test_seed_is_idempotent(db_session, seed_data, tmp_path):
    reg_fp = _write(tmp_path / 'regulation.yaml', """
        regulation: {short_code: NIS2, name: "NIS2", slug: nis2, status: in_force}
        obligations:
          - ref: "Art.21(2)(d)"
            title: "Supply chain"
    """)
    ctrl_fp = _write(tmp_path / 'controls.yaml', """
        controls:
          - {code: SC-01, title: "Supply-chain RM", domain: SupplyChain, checks: ["1.1"]}
    """)
    map_fp = _write(tmp_path / 'mappings.yaml', """
        regulation_slug: nis2
        mappings:
          - {control: SC-01, obligations: ["Art.21(2)(d)"]}
    """)
    for _ in range(2):
        seed_regulation_file(reg_fp)
        seed_controls_file(ctrl_fp)
        seed_mappings_file(map_fp)

    assert Regulation.query.filter_by(slug='nis2').count() == 1
    assert Obligation.query.filter_by(ref='Art.21(2)(d)').count() == 1
    control = Control.query.filter_by(code='SC-01').one()
    assert len(control.checks) == 1
    assert len(control.obligations) == 1
