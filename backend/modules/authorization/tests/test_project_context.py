from types import SimpleNamespace
from modules.authorization.application.customer_context import project_view

def test_project_view_does_not_expose_secret_or_storage_credentials():
    project=SimpleNamespace(id='p',workspace_id='w',name='Sample',description='',archived=False,rpm=30,concurrency=2,monthly_cap_milli=2_000,retention_hours=24,created_at=1,secret_key='DONOTREVEAL')
    result=project_view(project)
    assert result['id']=='p'
    assert 'secret_key' not in result
