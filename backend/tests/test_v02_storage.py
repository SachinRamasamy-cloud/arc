import hashlib,io
from urllib.parse import urlsplit
from sqlalchemy import select,func
from botocore.stub import Stubber
from botocore.response import StreamingBody
from arc.models import FileObject,StorageInterval,MultipartUpload,now
from arc.storage import ObjectStore,finish_upload
from conftest import call


def authorize(owner,body,**extra):
    base=f"/api/console/v1/projects/{owner['pid']}/files"
    r=call(owner['client'],'post',base,json={'name':'data.csv','size':len(body),'content_type':'text/csv','sha256':hashlib.sha256(body).hexdigest(),**extra})
    assert r.status_code==201,r.text
    return base,r.json()


def local_path(url):
    p=urlsplit(url);return p.path+'?'+p.query


def test_stored_file_retention_meter_and_delete(owner):
    data=b'name\nAda\n';base,session=authorize(owner,data,purpose='storage',retention_hours=720)
    c=owner['client'];assert c.put(local_path(session['upload_url']),content=data,headers=session['headers']).status_code==204
    complete=call(c,'post',base+'/'+session['file']['id']+'/complete');assert complete.status_code==200,complete.text
    assert complete.json()['purpose']=='storage' and complete.json()['expires_at']>now()+29*86400
    assert call(c,'post',base+'/'+session['file']['id']+'/complete').status_code==200
    with owner['db'].session() as db:assert db.scalar(select(func.count(StorageInterval.id)))==1
    assert call(c,'delete',base+'/'+session['file']['id']).status_code==200
    with owner['db'].session() as db:assert db.scalar(select(StorageInterval)).closed_at is not None


def test_checksum_mismatch_never_seals(owner):
    data=b'name\nAda\n';base,session=authorize(owner,data)
    owner['client'].put(local_path(session['upload_url']),content=b'name\nEve\n',headers=session['headers'])
    r=call(owner['client'],'post',base+'/'+session['file']['id']+'/complete');assert r.status_code==422,r.text
    with owner['db'].session() as db:
        assert db.get(FileObject,session['file']['id']).state=='pending'
        assert db.scalar(select(func.count(StorageInterval.id)))==0


def test_multipart_resume_complete_and_scope(owner):
    data=b'column\n'+b'a'*(5*1024*1024)+b'\n';base,session=authorize(owner,data)
    c=owner['client'];path=base+'/'+session['file']['id']+'/multipart'
    started=call(c,'post',path);assert started.status_code==200,started.text
    info=started.json();assert info['total_parts']==2 and info['parts']==[]
    assert call(c,'post',path+'/complete').status_code==409
    for number in range(1,3):
        signed=call(c,'post',path+f'/parts/{number}');assert signed.status_code==200,signed.text
        chunk=data[(number-1)*info['part_size']:number*info['part_size']]
        assert c.put(local_path(signed.json()['url']),content=chunk).status_code==200
        resume=call(c,'post',path).json();assert len(resume['parts'])==number
    result=call(c,'post',path+'/complete');assert result.status_code==200,result.text
    assert result.json()['digest']==hashlib.sha256(data).hexdigest()
    assert call(c,'post',path+'/complete').status_code==200
    with owner['db'].session() as db:assert db.scalar(select(func.count(StorageInterval.id)))==1
    assert call(c,'post',path).json()['state']=='complete'
    assert call(c,'post',path+'/parts/1').status_code==422


def test_abort_releases_reserved_storage(owner):
    base,session=authorize(owner,b'abc');c=owner['client'];path=base+'/'+session['file']['id']+'/multipart'
    assert call(c,'post',path).status_code==200
    assert call(c,'delete',path).json()['state']=='aborted'
    assert call(c,'delete',path).status_code==200
    assert call(c,'post',path).status_code==409


def test_r2_presign_and_stream_verification_contract(owner):
    # Boto3's real request/signing implementation + strict SDK stubbed responses.
    settings=owner['settings'].model_copy(update={'storage_mode':'r2','r2_endpoint':'https://example.r2.cloudflarestorage.com','r2_bucket':'private-bucket','r2_access_key':'test-key','r2_secret_key':'test-secret'})
    store=ObjectStore(settings);raw=b'{"private":true}'
    with owner['db'].session() as db:
        f=FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='test.json',content_type='application/json',expected_size=len(raw),object_key='tenant/staging/test',expires_at=now()+100,retention_hours=24)
        db.add(f);db.flush()
        url=store.upload_url(f);assert 'X-Amz-Signature=' in url and 'test-secret' not in url
        from botocore.stub import ANY
        with Stubber(store.client) as stub:
            stub.add_response('head_object',{'ContentLength':len(raw),'ETag':'"etag"'},{'Bucket':'private-bucket','Key':f.object_key})
            stub.add_response('get_object',{'Body':StreamingBody(io.BytesIO(raw),len(raw))},{'Bucket':'private-bucket','Key':f.object_key,'IfMatch':'"etag"'})
            stub.add_response('put_object',{}, {'Bucket':'private-bucket','Key':ANY,'Body':raw,'ContentType':'application/json'})
            stub.add_response('delete_object',{}, {'Bucket':'private-bucket','Key':f.object_key})
            result=finish_upload(db,store,f);assert result.state=='ready' and '/verified/' in result.object_key
            stub.assert_no_pending_responses()
