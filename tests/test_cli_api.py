import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from fastapi.testclient import TestClient

from backend import discovery
from backend.cli import request
from backend.service import create_app


def test_api_introspection_and_echo():
    with TestClient(create_app('test-token')) as client:
        headers = {'X-Calix-Token': 'test-token'}
        for path in ('capabilities', 'sessions', 'openapi.json'):
            assert client.get('/api/' + path).status_code == 403
        schema = client.get('/api/openapi.json', headers=headers).json()
        assert schema['components']['securitySchemes']['LocalToken']['name'] == 'X-Calix-Token'
        assert schema['paths']['/api/evaluate']['post']['security'] == [{'LocalToken': []}]
        result = client.post('/api/evaluate', headers=headers, json={
            'session': 'api-test', 'request_id': 'requested-123', 'code': 'x=41; x+1', 'timeout_seconds': 20}).json()
        assert result['ok'] and result['session'] == 'api-test' and result['request_id'] == 'requested-123'
        assert result['result']['text'] == '42'
        sessions = client.get('/api/sessions', headers=headers).json()['sessions']
        assert sessions[0]['session'] == 'api-test' and not sessions[0]['busy']
        assert 'token' not in json.dumps(sessions) and 'code' not in sessions[0]
        assert client.post('/api/shutdown', headers=headers).status_code == 409
        for timeout in (0, 3601, 'not-a-number'):
            assert client.post('/api/evaluate', headers=headers, json={
                'session': 's', 'code': '1', 'timeout_seconds': timeout}).status_code == 422


def test_connection_record_is_loopback_only(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    path = discovery.publish(12345, 'private-test-token', 'cli')
    record = discovery.read(path)
    assert record['url'] == 'http://127.0.0.1:12345' and record['pid'] == os.getpid()
    for url in ('http://example.com:12345', 'http://127.0.0.1:12345@evil.invalid/',
                'https://127.0.0.1:12345/', 'http://127.0.0.1:12345/evil'):
        record['url'] = url
        path.write_text(json.dumps(record), encoding='utf8')
        with pytest.raises(ValueError):
            discovery.read(path)


def test_discovery_process_lifetime():
    assert discovery.process_running(os.getpid())
    assert not discovery.process_running(0)
    process = subprocess.Popen([sys.executable, '-c', 'pass'])
    process.wait(timeout=10)
    assert not discovery.process_running(process.pid)


def test_connect_skips_dead_records_but_authenticates_live_pid(monkeypatch):
    from backend import cli
    monkeypatch.setattr(discovery, 'candidates', lambda: ['dead', 'reused', 'live'])
    monkeypatch.setattr(discovery, 'read', lambda path: {'pid': {'dead':1,'reused':2,'live':3}[path]})
    monkeypatch.setattr(discovery, 'process_running', lambda pid: pid != 1)
    probes = []
    def probe(connection, *args, **kwargs):
        probes.append(connection['pid'])
        return {'application':'Calix', 'pid':3}
    monkeypatch.setattr(cli, 'request', probe)
    assert cli.connect()['pid'] == 3
    assert probes == [2, 3]


@pytest.fixture(scope='module')
def local_service(tmp_path_factory):
    directory = tmp_path_factory.mktemp('cli-api')
    env = {**os.environ, 'LOCALAPPDATA': str(directory), 'CALIX_MAX_WORKERS': '2'}
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen([sys.executable, '-m', 'backend.service', '--publish-connection', '--role', 'cli', '--connection-id', 'test-service'],
                               cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    connection = None
    record_path = directory / 'com.calix.desktop/api/connection-test-service.json'
    try:
        ready = process.stdout.readline().split()
        assert ready[0] == 'CALIX_READY'
        connection = {'url': 'http://127.0.0.1:' + ready[1], 'token': ready[2]}
        connection = discovery.read(record_path)
        for _ in range(100):
            try:
                request(connection, '/capabilities')
                break
            except Exception:
                time.sleep(.05)
        yield env, root, connection
    finally:
        if process.poll() is None and connection:
            request(connection, '/shutdown', {})
        process.wait(timeout=15)
        assert not record_path.exists()


def run_cli(local_service, *arguments):
    env, root, _ = local_service
    command = [sys.executable, '-m', 'backend.cli', *arguments]
    process = subprocess.run(command, env=env, cwd=root, capture_output=True, text=True, encoding='utf8', timeout=30)
    return process.returncode, json.loads(process.stdout)


def test_cli_discovers_service_without_printing_credentials(local_service):
    status, result = run_cli(local_service, 'status')
    assert status == 0 and result['api_version'] == 1 and result['role'] == 'cli'
    assert local_service[2]['token'] not in json.dumps(result)
    status, result = run_cli(local_service, 'schema')
    assert status == 0 and '/api/evaluate' in result['paths']


def test_cli_keeps_and_resets_session_state(local_service):
    assert run_cli(local_service, 'eval', '--session', 'cli-test', '--code', 'x=41')[0] == 0
    status, result = run_cli(local_service, 'eval', '--session', 'cli-test', '--code', 'x+1')
    assert status == 0 and result['result']['text'] == '42'
    status, result = run_cli(local_service, 'sessions')
    assert status == 0 and any(s['session'] == 'cli-test' for s in result['sessions'])
    assert run_cli(local_service, 'reset', 'cli-test')[0] == 0
    assert run_cli(local_service, 'eval', '--session', 'cli-test', '--code', 'x')[1]['result']['text'] == 'x'


def test_cli_files_notebooks_and_error_exit_codes(local_service, tmp_path):
    code = tmp_path / 'units.wl'
    code.write_text('UnitConvert[650[gr],"g"]', encoding='utf8')
    output = tmp_path / 'out.json'
    status, response = run_cli(local_service, 'eval', '--file', str(code), '--output', str(output))
    assert status == 0 and response['output'] == str(output)
    assert json.loads(output.read_text(encoding='utf8'))['result']['text'].endswith('[g]')
    notebook = tmp_path / 'input.cixnb'
    notebook.write_text(json.dumps({'format': 'calix-notebook', 'version': 1, 'title': 'CLI', 'cells': [
        {'mode': 'markdown', 'code': '# context'}, {'mode': 'source', 'code': 'a=6;'},
        {'mode': 'source', 'code': 'a^2'}, {'mode': 'source', 'code': 'D[x^3,x]'}]}), encoding='utf8')
    status, result = run_cli(local_service, 'run', str(notebook))
    assert status == 0 and len(result['cells']) == 3
    assert result['cells'][1]['result']['text'] == '36'
    assert result['cells'][2]['result']['text'] == '3*x^2'
    assert run_cli(local_service, 'eval', '--code', 'Sin[')[0] == 1
    assert run_cli(local_service, 'eval', '--code', '1', '--timeout', '0')[0] == 2


@pytest.mark.skipif(os.name != 'nt', reason='Windows command launcher')
def test_command_launcher_preserves_caller_relative_paths(local_service, tmp_path):
    env, root, _ = local_service
    (tmp_path / 'input.wl').write_text('Sum[k^4,{k,1,100}]', encoding='utf8')
    process = subprocess.run([str(root / 'calix.cmd'), 'eval', '--file', 'input.wl',
                              '--output', 'output.json'], cwd=tmp_path, env=env,
                             capture_output=True, text=True, encoding='utf8', timeout=30)
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(process.stdout)['output'] == str(tmp_path / 'output.json')
    assert json.loads((tmp_path / 'output.json').read_text(encoding='utf8'))['result']['text'] == '2050333330'


@pytest.mark.skipif(os.name != 'nt', reason='Windows native command launcher')
def test_native_launcher_preserves_expression_arguments(local_service, tmp_path):
    env, root, _ = local_service
    launcher = root / 'calix-cli.exe'
    if not launcher.exists():
        pytest.skip('Run scripts/build-native.ps1 to build the launcher')
    for code, expected in [('2^3', '8'), ('If[2>1&&3>2,2^3,0]', '8'),
                            ('UnitConvert[1[kg*m/s^2],"N"]', '1[N]')]:
        process = subprocess.run([str(launcher), 'eval', '--code', code], cwd=tmp_path,
                                 env=env, capture_output=True, text=True, encoding='utf8', timeout=30)
        response = json.loads(process.stdout)
        assert process.returncode == 0, response
        assert response['result']['text'] == expected
    process = subprocess.run([str(root / 'calix.cmd'), 'eval', '--code', '2^3'], cwd=tmp_path,
                             env=env, capture_output=True, text=True, encoding='utf8', timeout=30)
    assert process.returncode == 2
    assert json.loads(process.stdout)['error_type'] == 'LauncherError'


def test_open_ui_command_is_independent_of_calculation_service(monkeypatch):
    from backend import cli
    monkeypatch.setattr(cli, 'open_user_interface', lambda: {'opened': True, 'pid': 123})
    assert cli.main(['open-ui']) == 0


def test_http_open_ui_requires_authentication(monkeypatch):
    from backend import launcher
    monkeypatch.setattr(launcher, 'open_user_interface', lambda: {'opened': True, 'pid': 123})
    with TestClient(create_app('test-token')) as client:
        assert client.post('/api/open-ui').status_code == 403
        response = client.post('/api/open-ui', headers={'X-Calix-Token': 'test-token'})
        assert response.status_code == 200 and response.json()['ui']['opened']


def test_handoff_preserves_results_source_and_unevaluated_cells(tmp_path, monkeypatch, capsys):
    from backend import cli
    source = tmp_path / 'input.cixnb'
    cells = [{'mode': 'markdown', 'code': '# Task'},
             {'mode': 'source', 'code': '1+1'},
             {'mode': 'source', 'code': 'Sin['},
             {'mode': 'source', 'code': '3+3'}]
    original = json.dumps({'format': 'calix-notebook', 'version': 1, 'title': 'Task', 'cells': cells})
    source.write_text(original, encoding='utf8')
    monkeypatch.setattr(cli, 'connect', lambda _: {})
    responses = iter([{'ok': True, 'result': {'text': '2'}}, {'ok': False, 'error': 'Invalid syntax'}])
    monkeypatch.setattr(cli, 'evaluate', lambda *args: next(responses))
    monkeypatch.setattr(cli, 'open_user_interface', lambda path: {'opened': True, 'notebook': str(path)})
    output = tmp_path / 'input.json'
    assert cli.main(['run', str(source), '--output', str(output), '--open-ui']) == 1
    result = json.loads(output.read_text(encoding='utf8'))
    handoff = json.loads(Path(result['ui']['notebook']).read_text(encoding='utf8'))
    assert source.read_text(encoding='utf8') == original
    assert len(handoff['cells']) == 4
    assert handoff['cells'][1]['result']['text'] == '2'
    assert handoff['cells'][2]['error'] == 'Invalid syntax'
    assert handoff['cells'][3] == cells[3]
    assert len(result['cells']) == 2


def test_handoff_launch_failure_keeps_calculation(tmp_path, monkeypatch, capsys):
    from backend import cli
    monkeypatch.setattr(cli, 'connect', lambda _: {})
    monkeypatch.setattr(cli, 'evaluate', lambda *args: {'ok': True, 'result': {'text': '42'}})
    def fail(path):
        raise OSError('Desktop unavailable')
    monkeypatch.setattr(cli, 'open_user_interface', fail)
    output = tmp_path / 'result.json'
    assert cli.main(['eval', '--code', '6*7', '--output', str(output), '--open-ui']) == 2
    result = json.loads(output.read_text(encoding='utf8'))
    assert result['ok'] and result['result']['text'] == '42'
    assert result['ui']['opened'] is False
    assert Path(result['ui']['notebook']).exists()


def test_launcher_explicit_path_and_notebook_arguments(tmp_path, monkeypatch):
    from backend import launcher
    exe = tmp_path / 'Calix.exe'
    exe.touch()
    notebook = tmp_path / 'a notebook.cixnb'
    notebook.write_text('{}', encoding='utf8')
    monkeypatch.setenv('CALIX_UI_PATH', str(exe))
    calls = []
    class Process:
        pid = 123
    def launch(command, **options):
        calls.append((command, options))
        return Process()
    monkeypatch.setattr(launcher.subprocess, 'Popen', launch)
    assert launcher.open_user_interface(notebook)['pid'] == 123
    assert calls[0][0] == [str(exe), '--notebook', str(notebook)]
    assert 'shell' not in calls[0][1]
    monkeypatch.setenv('CALIX_UI_PATH', str(tmp_path / 'missing.exe'))
    with pytest.raises(FileNotFoundError):
        launcher.find_ui()


def test_brief_stdout_contains_answers_but_saved_file_keeps_full_data(local_service, tmp_path):
    output = tmp_path / 'full.json'
    status,result = run_cli(local_service, 'eval', '--code', '1+1\nPlot[x,{x,0,1}]',
                            '--brief', '--output', str(output))
    assert status == 0
    assert result['result']['items'][0]['text'] == '2'
    assert result['result']['items'][1] == {'kind':'plot','plot_type':'curve'}
    saved = json.loads(output.read_text(encoding='utf8'))
    assert 'latex' in saved['result']['items'][0]
    assert saved['result']['items'][1]['traces']
    assert 'latex' not in result['result']['items'][0]


def test_pipe_flushes_each_answer_before_eof_and_recovers_from_bad_lines(local_service, tmp_path):
    env,root,_ = local_service
    output = tmp_path / 'pipe.json'
    process = subprocess.Popen([sys.executable,'-m','backend.cli','pipe','--brief','--output',str(output)],
        cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,encoding='utf8')
    try:
        for message,expected in [({'id':'a','code':'a=41'},'41'),({'id':2,'code':'a+1'},'42')]:
            process.stdin.write(json.dumps(message)+'\n')
            process.stdin.flush()
            answer=json.loads(process.stdout.readline())
            assert answer['ok'] and answer['id']==message['id'] and answer['result']['text']==expected
        for line in ('not json\n','[]\n','{"id":[],"code":"1"}\n','{"code":"Sin["}\n'):
            process.stdin.write(line)
            process.stdin.flush()
            assert json.loads(process.stdout.readline())['ok'] is False
        process.stdin.write('{"id":"after-error","code":"a+2"}\n')
        process.stdin.flush()
        assert json.loads(process.stdout.readline())['result']['text']=='43'
        process.stdin.close()
        assert process.wait(timeout=15)==1
        saved=json.loads(output.read_text(encoding='utf8'))
        assert len(saved['responses'])==7
        assert saved['responses'][0]['result']['latex']=='41'
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def test_pipe_handoff_at_eof_keeps_saved_outputs(tmp_path, monkeypatch, capsys):
    import io
    from backend import cli
    monkeypatch.setattr(cli,'connect',lambda _: {})
    monkeypatch.setattr(cli,'evaluate',lambda *args: {'ok':True,'result':{'kind':'expression','text':'42'}})
    monkeypatch.setattr(cli.sys,'stdin',io.StringIO('{"id":"a","code":"6*7"}\n'))
    def launch(path):
        saved=json.loads(Path(path).read_text(encoding='utf8'))
        assert saved['cells'][0]['code']=='6*7'
        assert saved['cells'][0]['result']['text']=='42'
        return {'opened':True,'notebook':str(path)}
    monkeypatch.setattr(cli,'open_user_interface',launch)
    assert cli.main(['pipe','--brief','--open-ui','--output',str(tmp_path/'out.json')])==0
    lines=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0]['result']['text']=='42'
    assert lines[1]['event']=='ui' and lines[1]['ui']['opened']


def test_cli_entry_does_not_import_web_framework():
    root=Path(__file__).resolve().parents[1]
    process=subprocess.run([sys.executable,'-X','importtime','-m','backend.entry','--cli','--help'],
        cwd=root,capture_output=True,text=True,encoding='utf8',timeout=15)
    assert process.returncode==0
    assert 'fastapi' not in process.stderr


def test_official_notebook_export_contains_outputs_and_no_bom(local_service, tmp_path):
    target=tmp_path/'answer.cixnb'
    output=tmp_path/'full.json'
    status,result=run_cli(local_service,'eval','--code','1+1\nSqrt[3]*Sqrt[Pi]',
        '--notebook',str(target),'--title','Test answer','--brief','--output',str(output))
    assert status==0 and result['notebook']==str(target)
    assert not target.read_bytes().startswith(b'\xef\xbb\xbf')
    saved=json.loads(target.read_text(encoding='utf8'))
    assert saved['title']=='Test answer'
    assert saved['cells'][0]['result']['items'][0]['text']=='2'
    assert saved['cells'][0]['result']['items'][1]['latex']==r'\sqrt{3 \pi}'
    assert run_cli(local_service,'validate',str(target))[1]['syntax_checked']


def test_validate_bom_notebook_without_service_or_mutation(tmp_path, monkeypatch, capsys):
    from backend import cli
    target=tmp_path/'bom.cixnb'
    notebook={'format':'calix-notebook','version':1,'title':'BOM',
        'cells':[{'mode':'markdown','code':'inside\ufefftext'},{'mode':'source','code':'1+1'}]}
    original=b'\xef\xbb\xbf'+json.dumps(notebook,ensure_ascii=False).encode('utf8')
    target.write_bytes(original)
    def forbidden(*args):
        raise AssertionError('Validation must not contact a service')
    monkeypatch.setattr(cli,'connect',forbidden)
    assert cli.main(['validate',str(target)])==0
    assert json.loads(capsys.readouterr().out)['cells']==2
    assert target.read_bytes()==original
    notebook['cells'][1]['code']='Sin['
    target.write_text(json.dumps(notebook),encoding='utf8')
    assert cli.main(['validate',str(target)])==2
    assert 'cell 2' in json.loads(capsys.readouterr().out)['error']


def test_export_rejects_input_output_collisions_before_connecting(tmp_path, monkeypatch, capsys):
    from backend import cli
    source=tmp_path/'input.cixnb'
    source.write_text('original',encoding='utf8')
    monkeypatch.setattr(cli,'connect',lambda *args: (_ for _ in ()).throw(AssertionError('Must fail before connecting')))
    assert cli.main(['run',str(source),'--notebook',str(source)])==2
    assert source.read_text(encoding='utf8')=='original'
    assert 'overwrite' in json.loads(capsys.readouterr().out)['error']
