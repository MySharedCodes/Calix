"""Validate local release contents and record outstanding publication requirements."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def licensing_findings(root, license_id):
    errors, pending = [], []
    portable = root/'release/Calix-portable'
    packaged_license = portable/'LICENSE'
    if packaged_license.is_file() and packaged_license.read_bytes() != (root/'LICENSE').read_bytes():
        errors.append('Portable LICENSE differs from the current application license; rebuild the distribution.')
    notices = portable/'notices/THIRD-PARTY-NOTICES.txt'
    if license_id == 'GPL-3.0-only':
        if notices.is_file() and 'Calix application code is proprietary.' in notices.read_text(encoding='utf-8'):
            errors.append('Portable third-party notices still declare the Calix application proprietary.')
        runtime_directories = [root/'release/components/pde/native', portable/'components/pde/native']
        if any(list(directory.glob('mkl*.dll')) or (directory/'libiomp5md.dll').is_file()
               for directory in runtime_directories):
            pending.append('GPLv3 compatibility of the bundled Intel oneMKL/OpenMP runtime remains unresolved; see docs/LICENSING.md.')
    elif license_id in (None, '', 'UNLICENSED', 'LicenseRef-Proprietary'):
        pending.append('Public application license remains undecided.')
    return errors, pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public', action='store_true', help='Fail while publication requirements remain pending')
    args = parser.parse_args()
    package = json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
    version = package['version']
    errors = []
    for name in ['README.md','README.zh-CN.md','LICENSE','SECURITY.md','CONTRIBUTING.md','docs/USER-GUIDE.md','docs/GETTING-STARTED.en.md','BUILD-INFO.json','notices/THIRD-PARTY-NOTICES.txt','notices/mpl-sources/eigen-3.4.0.zip']:
        path = ROOT/'release/Calix-portable'/name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f'Missing or empty portable resource: {name}')
    manifest = ROOT/'release/SHA256.json'
    if manifest.is_file():
        for item in json.loads(manifest.read_text(encoding='utf-8')):
            path = ROOT/'release'/item['file']
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                errors.append(f'Hash mismatch: {item["file"]}')
    else:
        errors.append('Missing SHA256.json')
    provenance = ROOT/'release/BUILD-INFO.json'
    if provenance.is_file():
        data = json.loads(provenance.read_text(encoding='utf-8'))
        if data['version'] != version: errors.append('Build provenance version mismatch')
        if data['source_dirty']: errors.append('Build provenance records uncommitted source changes')
    pending = ['Clean Windows installation and upgrade qualification is not yet recorded.',
               'AVX-512 and AMX execution require matching hardware.',
               'Independent users have not completed the beta acceptance checklist.']
    license_errors, license_pending = licensing_findings(ROOT, package.get('license'))
    errors.extend(license_errors)
    pending.extend(license_pending)
    remote = subprocess.run(['git','remote','get-url','origin'], cwd=ROOT, capture_output=True)
    if remote.returncode: pending.append('Public repository address remains undecided.')
    installer = ROOT/f'release/Calix_{version}_x64-setup.exe'
    if sys.platform == 'win32' and installer.is_file():
        result = subprocess.run(['powershell','-NoProfile','-Command', f"(Get-AuthenticodeSignature -LiteralPath '{installer}').Status.ToString()"], capture_output=True, text=True)
        if result.stdout.strip() != 'Valid': pending.append('Installer does not have a verified Authenticode signature.')
    record = {'version': version, 'application_license': package.get('license'), 'local_artifact_errors': errors, 'publication_pending': pending, 'local_artifacts_passed': not errors, 'public_release_ready': not errors and not pending}
    (ROOT/'release/RELEASE-CHECK.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2))
    return int(bool(errors) or (args.public and bool(pending)))


if __name__ == '__main__':
    raise SystemExit(main())
