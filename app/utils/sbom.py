"""SBOM parsing + intake for CycloneDX and SPDX JSON (Phase 4 m9).

Supports the Space Act / CSA2 supply-chain obligations by ingesting an SBOM file,
extracting its components, and linking it to a supplier.
"""
import json
from ..extensions import db
from ..models import SBOM, SBOMComponent


def _as_text(raw):
    return raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw


def _cyclonedx_components(doc):
    out = []
    for c in doc.get('components', []) or []:
        license_id = ''
        for lic in c.get('licenses', []) or []:
            node = lic.get('license') or {}
            license_id = node.get('id') or node.get('name') or lic.get('expression') or ''
            if license_id:
                break
        out.append({
            'name': c.get('name', ''),
            'version': c.get('version', ''),
            'purl': c.get('purl', ''),
            'license': license_id,
        })
    return out


def _spdx_components(doc):
    out = []
    for p in doc.get('packages', []) or []:
        purl = ''
        for ref in p.get('externalRefs', []) or []:
            if ref.get('referenceType') == 'purl':
                purl = ref.get('referenceLocator', '')
                break
        out.append({
            'name': p.get('name', ''),
            'version': p.get('versionInfo', ''),
            'purl': purl,
            'license': p.get('licenseConcluded') or p.get('licenseDeclared') or '',
        })
    return out


def parse_sbom(raw):
    """Parse a CycloneDX or SPDX JSON SBOM. Returns {format, components}."""
    doc = json.loads(_as_text(raw))
    if doc.get('bomFormat') == 'CycloneDX' or 'components' in doc:
        return {'format': 'cyclonedx', 'components': _cyclonedx_components(doc)}
    if 'spdxVersion' in doc or 'packages' in doc:
        return {'format': 'spdx', 'components': _spdx_components(doc)}
    return {'format': 'unknown', 'components': []}


def ingest_sbom(supplier, filename, raw):
    """Parse an SBOM and persist it (with components) against a supplier."""
    text = _as_text(raw)
    parsed = parse_sbom(text)
    sbom = SBOM(
        supplier_id=supplier.id,
        name=filename,
        format=parsed['format'],
        original_filename=filename,
        component_count=len(parsed['components']),
        raw_size=len(text),
    )
    db.session.add(sbom)
    db.session.flush()
    for comp in parsed['components']:
        if not comp['name']:
            continue
        db.session.add(SBOMComponent(
            sbom_id=sbom.id,
            name=comp['name'],
            version=comp['version'] or None,
            purl=comp['purl'] or None,
            license=comp['license'] or None,
        ))
    return sbom
