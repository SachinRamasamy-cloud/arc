"""Playground-level contracts from customer input through public-safe native execution."""
from conftest import call
from modules.executions.application.worker import process_one


def test_custom_fields_mapping_and_billing(owner):
    client = owner['client']
    path = f"/api/console/v1/projects/{owner['pid']}"
    request = {
        'operation':'normalize',
        'data':[{'company_name':' ARC ', 'contact':' INFO@EXAMPLE.TEST '}],
        'required_fields':[],
        'mappings':{'contact':'email'},
        'lowercase':['email'],
        'max_credits_milli':10000,
    }
    quote = call(client,'post',path+'/quote',json=request)
    assert quote.status_code == 200, quote.text
    assert quote.json()['estimated_milli'] > 0
    created = call(client,'post',path+'/jobs',json=request,headers={'Idempotency-Key':'playground-custom-fields'})
    assert created.status_code == 202, created.text
    job_id = created.json()['job']['id']
    assert process_one(owner['db'],owner['settings'],owner['app'].state.store)
    response = client.get(path+'/jobs/'+job_id)
    assert response.status_code == 200
    job = response.json()['job']
    assert job['state'] == 'succeeded'
    assert job['result']['output'] == [{'company_name':'ARC','email':'info@example.test'}]
    assert job['charged_milli'] == quote.json()['estimated_milli']
    repeated = call(client,'post',path+'/jobs',json=request,headers={'Idempotency-Key':'playground-custom-fields'})
    assert repeated.status_code == 202 and repeated.json()['created'] is False
    assert repeated.json()['job']['id'] == job_id


def test_csv_field_names_from_customer_input(owner):
    client = owner['client']
    path = f"/api/console/v1/projects/{owner['pid']}"
    request = {'operation':'csv_to_json', 'data':'custom_field,contact\nA,A@EXAMPLE.TEST\n', 'max_credits_milli':10000}
    created = call(client,'post',path+'/jobs',json=request,headers={'Idempotency-Key':'csv-custom-fields'})
    assert created.status_code == 202
    assert process_one(owner['db'],owner['settings'],owner['app'].state.store)
    job = client.get(path+'/jobs/'+created.json()['job']['id']).json()['job']
    assert job['result']['output'] == [{'custom_field':'A', 'contact':'A@EXAMPLE.TEST'}]


def test_missing_required_field_is_safe_failure_and_not_charged(owner):
    client = owner['client']
    path = f"/api/console/v1/projects/{owner['pid']}"
    request = {'operation':'validate','data':[{'present':'hello'}], 'required_fields':['missing'], 'max_credits_milli':10000}
    created = call(client,'post',path+'/jobs',json=request,headers={'Idempotency-Key':'missing-field'})
    assert created.status_code == 202
    assert process_one(owner['db'],owner['settings'],owner['app'].state.store)
    job = client.get(path+'/jobs/'+created.json()['job']['id']).json()['job']
    assert job['state']=='failed'
    assert job['error_code']=='INVALID_INPUT'
    assert job['charged_milli']==0
    assert job['billing_state']=='released'
