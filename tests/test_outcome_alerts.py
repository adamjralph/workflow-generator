"""Observable local delivery after the existing bounded outcome/remedy journey."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

import pytest

from agent_lab.alerts import deliver_outcome_alert
from agent_lab.remedy import run_with_remedy
from agent_lab.remedy_demo import ReportInput
from agent_lab.reference import TransformResult
from agent_lab.spec import JsonOutputExpectation, Route, TransformNode, WorkflowSpec


@pytest.fixture
def receiver():
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, dict(self.headers), self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(server.reply)
            self.send_header('Location', '/redirected')
            self.end_headers()
            self.wfile.write(b'private response')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.reply = 204
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, received, f'http://127.0.0.1:{server.server_port}/alerts'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def report(driver, case):
    spec = WorkflowSpec(entry='report', budget=1,
        nodes=(TransformNode(id='report', operation='write_report',
            expected_output=JsonOutputExpectation(file='report.json', required_fields=('title', 'body'))),),
        edges=(Route(source='report', outcome='done', target='COMPLETED'),),
        terminals=('COMPLETED', 'FAILED_VALIDATION', 'FAILED_BUDGET'))
    def bindings(output, complete=False):
        def write(state):
            (output / 'report.json').write_text(json.dumps({'title': state.title, **({'body': '\n'.join(state.items)} if complete else {})}))
            return TransformResult(state, 'unknown' if case == 'ineligible' else 'done')
        return {'write_report': write}
    def repair(output, failed):
        if case == 'repair_failed':
            raise RuntimeError('private callback content')
        return bindings(output, case == 'repaired')
    return run_with_remedy(spec, ReportInput(), bindings_factory=lambda output: bindings(output, case == 'passed'),
        repair_bindings_factory=repair, step_allowance=2,
        evidence_dir=Path(os.environ['WORKFLOW_VALIDATION_DIR']), driver=driver)


@pytest.mark.parametrize('driver', ['reference', 'graph'])
@pytest.mark.parametrize('case', ['exhausted', 'ineligible', 'repair_failed', 'passed', 'repaired'])
def test_report_journey_delivers_only_unresolved_outcomes(receiver, driver, case):
    server, received, endpoint = receiver
    result = report(driver, case)
    outcome_bytes = result.receipt_path.read_bytes()
    alert = deliver_outcome_alert(result, endpoint=endpoint)
    assert result.receipt_path.read_bytes() == outcome_bytes
    saved = json.loads(alert.receipt_path.read_text())
    assert saved['remedy_digest'] == hashlib.sha256(outcome_bytes).hexdigest()
    assert saved['original_run'] == result.original.run_id
    if result.passed:
        assert received == []
        assert saved['status'] == 'suppressed'
        assert saved['payload_digest'] is None
    else:
        assert len(received) == 1
        path, headers, body = received[0]
        message = json.loads(body)
        assert path == '/alerts'
        assert headers['Content-Type'] == 'application/json'
        assert headers['Idempotency-Key'] == result.original.run_id
        assert message['status'] == case
        assert message['expected']['required_fields'] == ['title', 'body']
        assert message['unmet']
        assert message['reserved_steps'] == result.receipt.reserved_steps
        assert message['repair_run'] == result.receipt.repair_run
        assert 'no further repair' in message['action']
        assert saved['status'] == 'delivered' and saved['http_status'] == 204
        assert saved['payload_digest'] == hashlib.sha256(body).hexdigest()
        assert b'Internal release checklist' not in body  # no output artifact content
    with pytest.raises(FileExistsError):
        deliver_outcome_alert(result, endpoint=endpoint)
    assert len(received) == (0 if result.passed else 1)
    assert endpoint not in alert.receipt_path.read_text()


@pytest.mark.parametrize('code', [302, 400, 500])
def test_failure_and_redirect_are_not_retried(receiver, code):
    server, received, endpoint = receiver
    server.reply = code
    result = report('reference', 'exhausted')
    alert = deliver_outcome_alert(result, endpoint=endpoint)
    assert alert.receipt.status == 'failed' and alert.receipt.http_status == code
    assert len(received) == 1 and received[0][0] == '/alerts'
    assert 'private response' not in alert.receipt_path.read_text()


def test_disconnected_receiver_is_failed_without_exception_content(receiver):
    server, received, endpoint = receiver
    server.shutdown()
    server.server_close()
    result = report('graph', 'exhausted')
    alert = deliver_outcome_alert(result, endpoint=endpoint, timeout=.1)
    assert alert.receipt.status == 'failed' and alert.receipt.http_status is None
    assert received == []
    with pytest.raises(FileExistsError):
        deliver_outcome_alert(result, endpoint=endpoint)


@pytest.mark.parametrize('endpoint', ['http://example.com:80/', 'http://localhost:80/', 'https://127.0.0.1:443/',
    'http://127.0.0.1/', 'http://user:secret@127.0.0.1:80/', 'http://127.0.0.1:80/?token=secret',
    'http://127.0.0.1:80/#fragment', 'http://127.0.0.1:80/\nheader'])
def test_endpoint_policy_rejects_before_reservation(endpoint):
    result = report('reference', 'exhausted')
    with pytest.raises(ValueError):
        deliver_outcome_alert(result, endpoint=endpoint)
    assert not (result.original.root / 'alert-reserved.json').exists()


@pytest.mark.parametrize('timeout', [0, -1, 6, float('inf'), float('nan'), True])
def test_timeout_is_bounded(receiver, timeout):
    _, received, endpoint = receiver
    result = report('reference', 'exhausted')
    with pytest.raises(ValueError):
        deliver_outcome_alert(result, endpoint=endpoint, timeout=timeout)
    assert received == []


@pytest.mark.parametrize('which', ['receipt', 'original', 'repair'])
def test_tampered_evidence_prevents_delivery(receiver, which):
    _, received, endpoint = receiver
    result = report('reference', 'exhausted')
    path = {'receipt': result.receipt_path, 'original': result.original.verdict_path,
            'repair': result.repair.verdict_path}[which]
    path.write_text('{}')
    with pytest.raises(ValueError):
        deliver_outcome_alert(result, endpoint=endpoint)
    assert received == []
    assert not (result.original.root / 'alert-reserved.json').exists()
