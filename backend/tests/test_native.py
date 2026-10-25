import csv,io,json,random,subprocess
import pytest
from arc.native import run_native
from arc.errors import PublicError

@pytest.mark.parametrize('operation,data,expected',[
 ('validate',[{'id':1}],[{'id':1}]),
 ('normalize',[{'name':'  Ada \t'}],[{'name':'Ada'}]),
 ('csv_to_json','id,name\r\n1,"a,b"\r\n',[{'id':'1','name':'a,b'}]),
 ('csv_to_json','id,name\n1,"a\nline"\n',[{'id':'1','name':'a\nline'}]),
 ('csv_to_json','id,name\n1,"a""b"\n',[{'id':'1','name':'a"b'}]),
 ('csv_to_json','\ufeffid,name\n1,明\n',[{'id':'1','name':'明'}]),
])
def test_real_native_operations(ctx,operation,data,expected):
    response=run_native(ctx['settings'],{'operation':operation,'data':data})
    assert response['output']==expected and response['engine_version']=='1.0.0'

@pytest.mark.parametrize('payload',[
 {'operation':'not_allowed','data':[]},
 {'operation':'validate','data':[{'name':'x'}],'required_fields':['id']},
 {'operation':'validate','data':[1]},
 {'operation':'csv_to_json','data':'id,id\n1,2'},
 {'operation':'csv_to_json','data':'id,name\n1'},
 {'operation':'csv_to_json','data':'id\n"unclosed'},
 {'operation':'csv_to_json','data':'id\n"closed"x'},
 {'operation':'normalize','data':[{'a':1,'b':2}],'mappings':{'a':'b'}},
 {'operation':'json_to_csv','data':[{'nested':{'a':1}}]},
])
def test_native_rejects_unsupported_inputs(ctx,payload):
    with pytest.raises(PublicError):run_native(ctx['settings'],payload)

def test_formula_protection(ctx):
    result=run_native(ctx['settings'],{'operation':'json_to_csv','data':[{'x':'=SUM(A1:A2)'}]})
    assert "'=SUM" in result['output']

def test_csv_roundtrip_property(ctx):
    random.seed(42)
    for _ in range(12):
        rows=[{'a':''.join(random.choice('abc ,"\n') for _ in range(8)),'b':str(random.randint(0,100))} for _ in range(3)]
        csv_result=run_native(ctx['settings'],{'operation':'json_to_csv','data':rows})
        result=run_native(ctx['settings'],{'operation':'csv_to_json','data':csv_result['output']})
        assert result['output']==rows

def test_malformed_json_never_exposes_native_error(ctx):
    run=subprocess.run([ctx['settings'].native_path],input=b'{broken',capture_output=True)
    assert run.returncode==2
    assert json.loads(run.stdout)=={'ok':False,'code':'INVALID_INPUT'}
    assert run.stderr==b''
