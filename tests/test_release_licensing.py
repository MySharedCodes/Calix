"""Release gates for the GPL transition and artifacts from earlier builds."""
import importlib.util
import json
from pathlib import Path
import tomllib

import pytest


spec = importlib.util.spec_from_file_location('calix_release_check', Path(__file__).resolve().parents[1]/'scripts/release-check.py')
release_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_check)


def test_application_and_installer_license_metadata_agree():
    root = Path(__file__).resolve().parents[1]
    package = json.loads((root/'package.json').read_text(encoding='utf-8'))
    lock = json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
    cargo = tomllib.loads((root/'src-tauri/Cargo.toml').read_text(encoding='utf-8'))
    bundle = json.loads((root/'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))['bundle']
    assert package['license'] == lock['packages']['']['license'] == cargo['package']['license'] == bundle['license'] == 'GPL-3.0-only'
    assert (root/'src-tauri'/bundle['licenseFile']).resolve() == root/'LICENSE'
    text = (root/'LICENSE').read_text(encoding='utf-8')
    assert 'Version 3, 29 June 2007' in text
    assert 'END OF TERMS AND CONDITIONS' in text


def test_old_packaged_license_is_rejected(tmp_path):
    (tmp_path/'LICENSE').write_text('GNU GPL version 3', encoding='utf-8')
    portable = tmp_path/'release/Calix-portable'
    portable.mkdir(parents=True)
    (portable/'LICENSE').write_text('All rights reserved.', encoding='utf-8')
    errors, pending = release_check.licensing_findings(tmp_path, 'GPL-3.0-only')
    assert len(errors) == 1 and 'rebuild' in errors[0]
    assert not pending


@pytest.mark.parametrize('directory', ['release/components/pde/native', 'release/Calix-portable/components/pde/native'])
@pytest.mark.parametrize('binary', ['mkl_rt.2.dll', 'libiomp5md.dll'])
def test_intel_runtime_requires_gpl_review(tmp_path, directory, binary):
    native = tmp_path/directory
    native.mkdir(parents=True)
    (native/binary).write_bytes(b'test runtime')
    errors, pending = release_check.licensing_findings(tmp_path, 'GPL-3.0-only')
    assert not errors
    assert len(pending) == 1 and 'Intel' in pending[0]


def test_old_application_notice_is_rejected(tmp_path):
    notices = tmp_path/'release/Calix-portable/notices'
    notices.mkdir(parents=True)
    (notices/'THIRD-PARTY-NOTICES.txt').write_text('Calix application code is proprietary.', encoding='utf-8')
    errors, pending = release_check.licensing_findings(tmp_path, 'GPL-3.0-only')
    assert len(errors) == 1 and 'notices' in errors[0]
    assert not pending


def test_matching_gpl_files_without_intel_have_no_licensing_findings(tmp_path):
    (tmp_path/'LICENSE').write_text('GNU GPL version 3', encoding='utf-8')
    portable = tmp_path/'release/Calix-portable'
    portable.mkdir(parents=True)
    (portable/'LICENSE').write_bytes((tmp_path/'LICENSE').read_bytes())
    assert release_check.licensing_findings(tmp_path, 'GPL-3.0-only') == ([], [])
