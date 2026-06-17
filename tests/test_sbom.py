"""Tests for SBOM parsing + intake (Phase 4 m9, CSA2 supply chain)."""
import json
from app.models import Supplier, SBOM, SBOMComponent
from app.utils import sbom as sbom_util


CYCLONEDX = json.dumps({
    "bomFormat": "CycloneDX", "specVersion": "1.5",
    "components": [
        {"name": "openssl", "version": "3.0.0", "purl": "pkg:deb/openssl@3.0.0",
         "licenses": [{"license": {"id": "Apache-2.0"}}]},
        {"name": "zlib", "version": "1.2.13"},
    ],
})

SPDX = json.dumps({
    "spdxVersion": "SPDX-2.3",
    "packages": [
        {"name": "libc", "versionInfo": "2.36", "licenseConcluded": "LGPL-2.1",
         "externalRefs": [{"referenceType": "purl",
                           "referenceLocator": "pkg:deb/libc@2.36"}]},
    ],
})


def test_parse_cyclonedx():
    parsed = sbom_util.parse_sbom(CYCLONEDX)
    assert parsed['format'] == 'cyclonedx'
    assert len(parsed['components']) == 2
    openssl = parsed['components'][0]
    assert openssl['name'] == 'openssl'
    assert openssl['version'] == '3.0.0'
    assert openssl['purl'] == 'pkg:deb/openssl@3.0.0'
    assert openssl['license'] == 'Apache-2.0'


def test_parse_non_dict_json_is_unknown():
    # a bare JSON array must not raise (was an AttributeError -> 500)
    parsed = sbom_util.parse_sbom('[1, 2, 3]')
    assert parsed['format'] == 'unknown'
    assert parsed['components'] == []


def test_parse_spdx():
    parsed = sbom_util.parse_sbom(SPDX)
    assert parsed['format'] == 'spdx'
    assert parsed['components'][0]['name'] == 'libc'
    assert parsed['components'][0]['version'] == '2.36'
    assert parsed['components'][0]['purl'] == 'pkg:deb/libc@2.36'
    assert parsed['components'][0]['license'] == 'LGPL-2.1'


def test_ingest_sbom_creates_components(db_session):
    supplier = Supplier(name='Acme Sat Components', criticality='high')
    db_session.session.add(supplier)
    db_session.session.flush()

    sbom = sbom_util.ingest_sbom(supplier, 'bom.json', CYCLONEDX)
    db_session.session.commit()

    assert sbom.format == 'cyclonedx'
    assert sbom.component_count == 2
    assert sbom.supplier_id == supplier.id
    comps = SBOMComponent.query.filter_by(sbom_id=sbom.id).all()
    assert {c.name for c in comps} == {'openssl', 'zlib'}
