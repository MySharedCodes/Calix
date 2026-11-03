"""JSON command-line client for the same service used by Calix Notebook."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from backend import discovery
from backend.launcher import open_user_interface

_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class ClientError(Exception):
    pass


def request(connection, path, body=None, timeout=10):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf8')
    req = urllib.request.Request(connection['url'] + '/api' + path, data=data,
                                 headers={'X-Calix-Token': connection['token'], 'Content-Type': 'application/json'})
    try:
        with _http.open(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.load(exc).get('detail', exc.reason)
        except (ValueError, OSError):
            detail = exc.reason
        raise ClientError(f'HTTP {exc.code}: {detail}') from None
    except (OSError, ValueError) as exc:
        raise ClientError(f'Local API connection failed: {type(exc).__name__}') from None


def connect(path=None):
    for candidate in [Path(path)] if path else discovery.candidates():
        try:
            connection = discovery.read(candidate)
            if not discovery.process_running(connection['pid']):
                continue
            capabilities = request(connection, '/capabilities', timeout=2)
            if capabilities.get('application') == 'Calix' and capabilities.get('pid') == connection['pid']:
                return connection
        except (KeyError, ValueError, OSError, ClientError):
            continue
    return None


def service_command():
    return [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'backend.service']


def start(workers=None):
    identifier = uuid.uuid4().hex
    command = service_command() + ['--port', '0', '--publish-connection', '--role', 'cli', '--connection-id', identifier]
    if workers is not None:
        command += ['--workers', str(workers)]
    options = {'cwd': str(Path(sys.executable).parent) if getattr(sys, 'frozen', False)
               else str(Path(__file__).resolve().parents[1]), 'stdin': subprocess.DEVNULL,
               'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_BREAKAWAY_FROM_JOB
    else:
        options['start_new_session'] = True
    try:
        process = subprocess.Popen(command, **options)
    except OSError:
        if os.name != 'nt':
            raise
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(command, **options)
    path = discovery.directory() / f'connection-{identifier}.json'
    for _ in range(150):
        if process.poll() is not None:
            raise ClientError('Calix service did not start')
        connection = connect(path)
        if connection:
            return connection
        time.sleep(.1)
    process.terminate()
    process.wait(timeout=5)
    raise ClientError('Calix service startup timed out')


def load_file(path):
    path = Path(path)
    if path.stat().st_size > 10_000_000:
        raise ClientError('Input file exceeds 10 MB')
    return path.read_text(encoding='utf-8-sig')


def write_json(path, value):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=target.name + '.', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return str(target)


def load_notebook(path, check_code=False):
    notebook = json.loads(load_file(path))
    if (not isinstance(notebook, dict) or notebook.get('format') != 'calix-notebook'
            or notebook.get('version') != 1 or not isinstance(notebook.get('cells'), list)
            or not 1 <= len(notebook['cells']) <= 200):
        raise ClientError('Expected a Calix notebook v1 with 1 to 200 cells')
    if not isinstance(notebook.get('title', ''), str) or len(notebook.get('title', '')) > 200:
        raise ClientError('Notebook title must be a string of at most 200 characters')
    for index, cell in enumerate(notebook['cells']):
        if (not isinstance(cell, dict) or not isinstance(cell.get('code'), str)
                or len(cell['code']) > 24000 or cell.get('mode') not in ('source', 'math', 'markdown')):
            raise ClientError(f'Invalid notebook cell {index + 1}')
        if 'latex' in cell and (not isinstance(cell['latex'], str) or len(cell['latex']) > 24000):
            raise ClientError(f'Invalid formula in cell {index + 1}')
        if check_code and cell['mode'] != 'markdown' and cell['code'].strip():
            from backend.syntax import parse, InputError
            try:
                parse(cell['code'])
            except InputError as exc:
                raise ClientError(f'Invalid calculation syntax in cell {index + 1}: {exc}') from None
    return notebook


def evaluate(connection, session, code, timeout):
    request_id = str(uuid.uuid4())
    try:
        return request(connection, '/evaluate', {'session': session, 'code': code, 'request_id': request_id,
                                                'timeout_seconds': timeout}, timeout=timeout + 10)
    except KeyboardInterrupt:
        request(connection, '/cancel/' + session, {})
        raise


def brief_response(response):
    value = dict(response)
    if 'result' in value:
        def brief_result(result):
            if result.get('kind') == 'expression':
                return {key:result[key] for key in ('kind', 'text', 'label', 'unresolved')
                        if key in result and (key != 'unresolved' or result[key])}
            if result.get('kind') == 'group':
                return {'kind':'group', 'items':[brief_result(item) for item in result['items']],
                        **({'label':result['label']} if 'label' in result else {})}
            # Plot and animation data remain available in the full output file.
            return {key:result[key] for key in ('kind', 'plot_type', 'label') if key in result}
        value['result'] = brief_result(value['result'])
    if 'cells' in value:
        value['cells'] = [brief_response(cell) for cell in value['cells']]
    value.pop('request_id', None)
    return value


def display_cell(code, response, index):
    return {'id':uuid.uuid4().hex, 'mode':'source', 'code':code,
            **({'result':response['result'], 'executed':index} if response['ok']
               else {'error':response.get('error', 'Calculation failed')})}


def save_results(cells, title='AI calculation', output=None, notebook_path=None):
    display = {'format':'calix-notebook', 'version':1, 'title':title, 'cells':cells}
    if not 1 <= len(cells) <= 200 or len(json.dumps(display, ensure_ascii=False).encode('utf8')) > 10_000_000:
        raise ClientError('Notebook export requires 1 to 200 cells and at most 10 MB')
    folder = Path(output).resolve().parent if output else discovery.directory().parent / 'handoffs'
    path = Path(notebook_path).resolve() if notebook_path else folder / ('calix-handoff-' + uuid.uuid4().hex + '.cixnb')
    return write_json(path, display)


def open_results(cells, title='AI calculation', output=None, notebook_path=None):
    try:
        path = save_results(cells, title, output, notebook_path)
    except ClientError as exc:
        return {'opened':False, 'error':str(exc)}
    try:
        return open_user_interface(path)
    except (OSError, ValueError) as exc:
        return {'opened':False, 'notebook':str(Path(path).resolve()), 'error':str(exc)}


def pipe_requests(connection, args):
    """Keep client startup and discovery outside the per-expression round trip."""
    session = args.session or 'cli_pipe_' + uuid.uuid4().hex
    cells, responses = [], []
    failed = False
    while True:
        line = sys.stdin.readline(200001)
        if not line:
            break
        if not line.strip():
            continue
        identifier = None
        try:
            if len(line) > 200000:
                while line and not line.endswith('\n'):
                    line = sys.stdin.readline(200001)
                raise ValueError('JSONL request exceeds 200,000 characters')
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError('Expected a JSON object with a code string')
            identifier = message.get('id')
            if identifier is not None and (not isinstance(identifier, (str, int)) or len(str(identifier)) > 200):
                identifier = None
                raise ValueError('id must be a string or integer of at most 200 characters')
            code = message.get('code')
            if not isinstance(code, str) or not code.strip() or len(code) > 24000:
                raise ValueError('code must contain 1 to 24,000 characters')
            response = evaluate(connection, session, code, args.timeout)
            if args.open_ui or args.notebook:
                cells.append(display_cell(code, response, len(cells)+1))
        except (ValueError, ClientError) as exc:
            response = {'ok':False, 'error':str(exc), 'error_type':type(exc).__name__}
        if identifier is not None:
            response['id'] = identifier
        failed |= not response.get('ok', False)
        if args.output:
            responses.append(response)
        print(json.dumps(brief_response(response) if args.brief else response, ensure_ascii=False, allow_nan=False), flush=True)
    if args.output:
        write_json(args.output, {'ok':not failed, 'session':session, 'responses':responses})
    if args.notebook and cells and not args.open_ui:
        path = save_results(cells, args.title, args.output, args.notebook)
        print(json.dumps({'event':'notebook', 'ok':True, 'notebook':path}, ensure_ascii=False), flush=True)
    if args.open_ui and cells:
        ui = open_results(cells, args.title, args.output, args.notebook)
        print(json.dumps({'event':'ui', 'ok':ui['opened'], 'ui':ui}, ensure_ascii=False), flush=True)
        if not ui['opened']:
            return 2
    return 1 if failed else 0


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf8')
        sys.stderr.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser(prog='calix', description='Calix local calculation API client')
    parser.add_argument('--connection-file', help='Use one explicit local connection record')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='Show connection, version and CPU settings')
    commands.add_parser('sessions', help='List calculation sessions')
    commands.add_parser('schema', help='Print the API OpenAPI document')
    validate = commands.add_parser('validate', help='Validate notebook structure, encoding and calculation syntax without evaluating')
    validate.add_argument('file')
    boot = commands.add_parser('start', help='Start a headless service if none is running')
    boot.add_argument('--workers', type=int)
    commands.add_parser('stop', help='Stop a CLI-owned service (the desktop remains open)')
    ui = commands.add_parser('open-ui', help='Open the Calix desktop after an AI-controlled run')
    ui.add_argument('--notebook', help='Display an existing notebook, including saved results')
    settings = commands.add_parser('workers', help='Set the maximum CPU Workers count')
    settings.add_argument('count', type=int)
    for name in ('cancel', 'reset'):
        stop = commands.add_parser(name, help='Cancel a session and clear its variables')
        stop.add_argument('session')
    calculation = commands.add_parser('eval', help='Evaluate Wolfram-language input')
    source = calculation.add_mutually_exclusive_group(required=True)
    source.add_argument('--code')
    source.add_argument('--file')
    source.add_argument('--stdin', action='store_true')
    calculation.add_argument('--session', default='cli')
    calculation.add_argument('--timeout', type=float, default=180)
    calculation.add_argument('--output', help='Write the complete response to a JSON file')
    calculation.add_argument('--open-ui', action='store_true', help='Open the desktop when this operation finishes')
    calculation.add_argument('--brief', action='store_true', help='Return compact answers on stdout; --output still saves full results')
    calculation.add_argument('--notebook', help='Export an evaluated .cixnb using the official serializer')
    calculation.add_argument('--title', default='AI calculation')
    run = commands.add_parser('run', help='Run the calculation cells in a CIX notebook in order')
    run.add_argument('file')
    run.add_argument('--session')
    run.add_argument('--timeout', type=float, default=180)
    run.add_argument('--output')
    run.add_argument('--open-ui', action='store_true', help='Open the desktop when this operation finishes')
    run.add_argument('--brief', action='store_true', help='Return compact answers on stdout; --output still saves full results')
    run.add_argument('--notebook', help='Export an evaluated .cixnb without modifying the input')
    run.add_argument('--title')
    pipe = commands.add_parser('pipe', help='Persistent JSONL client: one {"id":...,"code":...} request and response per line')
    pipe.add_argument('--session')
    pipe.add_argument('--timeout', type=float, default=180)
    pipe.add_argument('--brief', action='store_true')
    pipe.add_argument('--output', help='Save full responses to JSON at EOF')
    pipe.add_argument('--open-ui', action='store_true', help='Open inputs and results at EOF')
    pipe.add_argument('--notebook', help='Export evaluated .cixnb at EOF')
    pipe.add_argument('--title', default='AI calculation')
    args = parser.parse_args(argv)
    try:
        if getattr(args, 'title', None) is not None and len(args.title) > 200:
            raise ClientError('Notebook title exceeds 200 characters')
        destinations = [Path(value).resolve() for value in (getattr(args,'output',None),getattr(args,'notebook',None)) if value]
        if len(set(destinations)) != len(destinations):
            raise ClientError('JSON output and notebook output must use different paths')
        if getattr(args,'file',None) and Path(args.file).resolve() in destinations:
            raise ClientError('An output path cannot overwrite the input file')
        if args.command != 'open-ui' and getattr(args,'notebook',None) and Path(args.notebook).suffix.lower() != '.cixnb':
            raise ClientError('Notebook output must use the .cixnb extension')
        if args.command == 'validate':
            notebook = load_notebook(args.file, check_code=True)
            print(json.dumps({'ok':True, 'file':str(Path(args.file).resolve()), 'title':notebook.get('title',''),
                'cells':len(notebook['cells']), 'saved_results':sum('result' in cell for cell in notebook['cells']),
                'encoding':'UTF-8 (optional leading BOM)', 'syntax_checked':True}, ensure_ascii=False))
            return 0
        if args.command == 'open-ui':
            result = {'ok': True, 'ui': open_user_interface(args.notebook) if args.notebook else open_user_interface()}
            print(json.dumps(result, ensure_ascii=False))
            return 0
        connection = connect(args.connection_file)
        if connection is None:
            if args.connection_file or args.command in ('status', 'sessions', 'schema', 'stop', 'reset', 'cancel', 'workers', 'open-ui'):
                raise ClientError('No running Calix API service; use calix start or open Calix')
            connection = start(getattr(args, 'workers', None))
        if args.command == 'pipe':
            return pipe_requests(connection, args)
        if args.command == 'start':
            if args.workers is not None:
                request(connection, '/settings', {'max_workers': args.workers})
            result = {'ok': True, 'url': connection['url'], 'pid': connection['pid'], 'role': connection['role']}
        elif args.command == 'status':
            result = {'ok': True, 'url': connection['url'], 'pid': connection['pid'], 'role': connection['role'],
                      **request(connection, '/health')}
        elif args.command == 'sessions':
            result = request(connection, '/sessions')
        elif args.command == 'schema':
            result = request(connection, '/openapi.json')
        elif args.command == 'workers':
            result = request(connection, '/settings', {'max_workers': args.count})
        elif args.command == 'stop':
            result = request(connection, '/shutdown', {})
        elif args.command in ('cancel', 'reset'):
            if not args.session.isascii() or not args.session.replace('-', '').replace('_', '').isalnum():
                raise ClientError('Invalid session identifier')
            result = request(connection, '/cancel/' + args.session, {})
        elif args.command == 'eval':
            code = load_file(args.file) if args.file else sys.stdin.read(24001) if args.stdin else args.code
            result = evaluate(connection, args.session, code, args.timeout)
            display_cells = [display_cell(code, result, 1)]
        else:
            notebook = load_notebook(args.file)
            session = args.session or 'cli_run_' + uuid.uuid4().hex
            results = []
            display_cells = []
            for index, cell in enumerate(notebook['cells']):
                if cell.get('mode') == 'markdown' or not cell.get('code', '').strip():
                    display_cells.append(cell)
                    continue
                if cell.get('mode') not in ('source', 'math'):
                    raise ClientError(f'Invalid calculation cell {index + 1}')
                item = evaluate(connection, session, cell['code'], args.timeout)
                results.append({'cell': index + 1, 'id': cell.get('id'), **item})
                display_cells.append(display_cell(cell['code'], item, len(results)))
                if not item['ok']:
                    display_cells.extend(notebook['cells'][index + 1:])
                    break
            result = {'ok': all(item['ok'] for item in results), 'session': session, 'title': notebook.get('title', 'AI calculation'), 'cells': results}
        if getattr(args, 'notebook', None) or getattr(args, 'open_ui', False):
            display_title = (args.title or notebook.get('title', 'AI calculation')) if args.command == 'run' else args.title
        if getattr(args, 'notebook', None) and not args.open_ui:
            result['notebook'] = save_results(display_cells, display_title, args.output, args.notebook)
        if getattr(args, 'open_ui', False):
            result['ui'] = open_results(display_cells,
                display_title, args.output, args.notebook)
            if args.notebook and 'notebook' in result['ui']:
                result['notebook'] = result['ui']['notebook']
        if getattr(args, 'output', None):
            path = write_json(args.output, result)
            summary = {**brief_response(result), 'output':path} if args.brief else {'ok': result.get('ok', True), 'output': path}
            if 'cells' in result:
                summary['evaluated_cells'] = len(result['cells'])
            if 'ui' in result:
                summary['ui'] = result['ui']
            if 'notebook' in result:
                summary['notebook'] = result['notebook']
            print(json.dumps(summary, ensure_ascii=False))
        else:
            print(json.dumps(brief_response(result) if getattr(args, 'brief', False) else result, ensure_ascii=False, allow_nan=False))
        return 2 if result.get('ui', {}).get('opened') is False else 0 if result.get('ok', True) else 1
    except KeyboardInterrupt:
        print(json.dumps({'ok': False, 'error': 'Cancelled', 'error_type': 'Cancelled'}))
        return 130
    except (ClientError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'error_type': type(exc).__name__}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
