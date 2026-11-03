"""Per-user discovery records for authenticated local computation services."""
import json
import os
import re
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit


def directory():
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local/share')
    return base / 'com.calix.desktop/api'


def publish(port, token, role, identifier=None):
    identifier = identifier or str(os.getpid())
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', identifier):
        raise ValueError('Invalid connection identifier')
    target = directory() / f'connection-{identifier}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {'format': 'calix-local-api', 'api_version': 1, 'pid': os.getpid(),
              'url': f'http://127.0.0.1:{port}', 'token': token, 'role': role, 'created': time.time()}
    descriptor, temporary = tempfile.mkstemp(prefix='.connection-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf8') as stream:
            json.dump(record, stream)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def read(path):
    path = Path(path)
    if path.stat().st_size > 8192:
        raise ValueError('Invalid local connection record')
    record = json.loads(path.read_text(encoding='utf8'))
    address = urlsplit(record['url'])
    if record.get('format') != 'calix-local-api' or record.get('api_version') != 1 or address.scheme != 'http' \
            or address.hostname != '127.0.0.1' or address.username or address.password or address.path not in ('', '/') \
            or address.query or address.fragment or not address.port or not 1 <= address.port <= 65535 \
            or not isinstance(record.get('token'), str) or not 1 <= len(record['token']) <= 256 \
            or not isinstance(record.get('pid'), int) or record.get('role') not in ('desktop', 'cli'):
        raise ValueError('Invalid local connection record')
    record['url'] = f'http://127.0.0.1:{address.port}'
    return record


def candidates():
    return sorted(directory().glob('connection-*.json'), key=lambda path: path.stat().st_mtime, reverse=True)


def process_running(pid):
    """Skip abandoned records before attempting a potentially slow HTTP probe."""
    if pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            # Access denied is inconclusive; keep the authenticated HTTP check.
            return ctypes.get_last_error() != 87
        try:
            return kernel.WaitForSingleObject(handle, 0) != 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True
