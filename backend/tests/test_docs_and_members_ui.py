"""Regression: docs route stays public/sanitized and team directory has useful read access."""
from conftest import account, call
from arc.models import Token
from arc.security import digest
from foundation.clock import now


def test_docs_works_and_does_not_publish_staff_schema(ctx):
    response = ctx['client'].get('/docs')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    assert 'Developer API' in response.text
    assert '/v1/jobs' in response.text
    assert '/api/operator/' not in response.text
    assert 'sk_live_' not in response.text
    assert 'password_hash' not in response.text
    assert ctx['client'].get('/docs/').status_code == 200
    schema = ctx['client'].get('/v1/openapi.json')
    assert schema.status_code == 200
    assert all(not path.startswith('/api/operator') for path in schema.json()['paths'])


def test_members_load_for_owner_and_viewer_without_invite_exposure(owner):
    wid=owner['wid'];url=f'/api/console/v1/workspaces/{wid}/members'
    response=owner['client'].get(url)
    assert response.status_code==200
    assert response.json()['can_manage'] is True
    assert len(response.json()['items'])==1
    assert response.json()['items'][0]['role']=='owner'
    viewer, user_id=account(owner, 'readonly@example.com', role='viewer', wid=wid)
    try:
        with owner['db'].session() as db:
            db.add(Token(id=digest('invitation-for-test'),purpose='invite',payload={'workspace_id':wid,'email':'private@example.com','role':'developer'},expires_at=now()+3600))
            db.commit()
        response=viewer.get(url)
        assert response.status_code==200
        assert len(response.json()['items'])==2
        assert response.json()['invites']==[]
        assert response.json()['can_manage'] is False
        denied=call(viewer,'post',url+'/invite',json={'email':'outsider@example.com','role':'developer'})
        assert denied.status_code==403
        assert owner['client'].get(url).json()['invites'][0]['email']=='private@example.com'
    finally:
        viewer.close()
