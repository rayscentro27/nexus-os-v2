import json
from pathlib import Path
import pytest
from nexus_agent_platform.google_workspace import SCOPES, validate_client_secrets, validate_scopes, certify_read_only, build_google_credentials
from nexus_agent_platform import credential_control_plane as cp

def test_exact_scopes_only():
    assert validate_scopes(SCOPES)
    assert not validate_scopes(SCOPES + ["https://www.googleapis.com/auth/gmail.send"])
    assert not validate_scopes(["https://www.googleapis.com/auth/cloud-platform"])

def test_client_json_desktop_validation(tmp_path):
    p=tmp_path/'client.json'; p.write_text(json.dumps({'installed':{'client_id':'id','client_secret':'secret','auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token'}}))
    assert validate_client_secrets(p)['client_id']=='id'
    bad=tmp_path/'bad.json'; bad.write_text('{}')
    with pytest.raises(ValueError): validate_client_secrets(bad)

def test_repo_local_client_file_rejected(tmp_path):
    # The implementation refuses any client JSON under the repository root.
    with pytest.raises(ValueError): validate_client_secrets(Path(__file__).parents[3]/'configs/nexus_credential_registry.json')

def test_missing_google_credential_is_truthful(monkeypatch):
    monkeypatch.setattr('nexus_agent_platform.google_workspace.keychain_status', lambda *_: 'NOT_FOUND')
    result=certify_read_only()
    assert result['status']=='GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED'
    assert result['mutations_performed'] is False
    assert result['secret_values_exposed'] is False

def test_keychain_writer_and_reader_share_service_account(monkeypatch):
    calls=[]
    class Proc:
        returncode=0; stdout=''; stderr=''
    fixture_value = 'fixture-value'
    monkeypatch.setattr(cp, '_keychain_value', lambda credential_id, component: None)
    monkeypatch.setattr(cp.subprocess, 'run', lambda args, **kwargs: calls.append(args) or Proc())
    cp.store_keychain('credential.google.workspace.prod.v1','client_id',fixture_value)
    monkeypatch.setattr(cp, '_keychain_value', lambda credential_id, component: fixture_value)
    assert cp.keychain_status('credential.google.workspace.prod.v1','client_id') == 'CONFIGURED'
    assert calls[0][calls[0].index('-s')+1] == 'nexus/credential.google.workspace.prod.v1'
    assert calls[0][calls[0].index('-a')+1] == 'client_id'
    assert fixture_value not in json.dumps(cp.resolve('credential.google.workspace.prod.v1', environ={}))

def test_credentials_use_refresh_token_only():
    class FakeCredentials:
        def __init__(self, **kwargs): self.kwargs=kwargs
    creds=build_google_credentials(FakeCredentials, client_id='id', client_secret='secret', refresh_token='refresh')
    assert creds.kwargs['token'] is None
    assert creds.kwargs['refresh_token'] == 'refresh'
