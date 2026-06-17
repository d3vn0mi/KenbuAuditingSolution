"""Tests for the regulatory YAML schema validator."""
import textwrap

from scripts.validate_regulations import validate_data_dir


def _build_valid_tree(root):
    (root / 'regulations' / 'nis2').mkdir(parents=True)
    (root / 'controls').mkdir()
    (root / 'mappings').mkdir()
    (root / 'regulations' / 'nis2' / 'regulation.yaml').write_text(textwrap.dedent("""
        regulation:
          short_code: NIS2
          name: "NIS2 Directive"
          slug: nis2
          status: in_force
        obligations:
          - ref: "Art.21(2)(d)"
            title: "Supply chain"
    """))
    (root / 'controls' / 'controls.yaml').write_text(textwrap.dedent("""
        controls:
          - code: SC-01
            title: "Supply-chain RM"
            domain: SupplyChain
            references:
              - {framework: ISO27001, ref_code: "A.5.19", title: "Suppliers"}
    """))
    (root / 'mappings' / 'nis2.yaml').write_text(textwrap.dedent("""
        regulation_slug: nis2
        mappings:
          - control: SC-01
            obligations: ["Art.21(2)(d)"]
    """))


def test_valid_tree_has_no_errors(tmp_path):
    _build_valid_tree(tmp_path)
    errors = validate_data_dir(str(tmp_path))
    assert errors == []


def test_regulation_missing_required_field_is_error(tmp_path):
    _build_valid_tree(tmp_path)
    (tmp_path / 'regulations' / 'nis2' / 'regulation.yaml').write_text(textwrap.dedent("""
        regulation:
          short_code: NIS2
          slug: nis2
          status: in_force
    """))  # missing required 'name'
    errors = validate_data_dir(str(tmp_path))
    assert any('name' in e for e in errors)


def test_mapping_to_unknown_control_is_error(tmp_path):
    _build_valid_tree(tmp_path)
    (tmp_path / 'mappings' / 'nis2.yaml').write_text(textwrap.dedent("""
        regulation_slug: nis2
        mappings:
          - control: DOES-NOT-EXIST
            obligations: ["Art.21(2)(d)"]
    """))
    errors = validate_data_dir(str(tmp_path))
    assert any('DOES-NOT-EXIST' in e for e in errors)


def test_invalid_reference_framework_is_error(tmp_path):
    _build_valid_tree(tmp_path)
    (tmp_path / 'controls' / 'controls.yaml').write_text(textwrap.dedent("""
        controls:
          - code: SC-01
            title: "Supply-chain RM"
            references:
              - {framework: NOT_A_FRAMEWORK, ref_code: "x"}
    """))
    errors = validate_data_dir(str(tmp_path))
    assert any('NOT_A_FRAMEWORK' in e for e in errors)
