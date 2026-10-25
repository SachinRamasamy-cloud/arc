"""First-party service catalog; no runtime external-provider registry."""
OPERATIONS=('validate','normalize','csv_to_json','json_to_csv')

CATALOG=[
 {'id':'data','name':'Data processing','status':'available','description':'Validate, normalize and convert JSON and CSV.','operations':list(OPERATIONS),'engine':'1.0.0'},
 {'id':'files','name':'Files for processing','status':'available','description':'Private verified JSON/CSV/text files up to 16 MB, with configurable retention and resumable uploads.','operations':['upload','download','delete']},
 {'id':'events','name':'Execution events','status':'available','description':'Live progress and signed completion delivery.','operations':['sse','webhooks']},
 {'id':'records','name':'Application data','status':'available','description':'Encrypted project-scoped JSON records with version checks. Not a relational database or identity service.','operations':['read','write','list','delete']},
 {'id':'identity','name':'Identity','status':'roadmap','description':'Application accounts and authentication. Not available for purchase.','operations':[]},
 {'id':'realtime','name':'Application realtime','status':'roadmap','description':'General application channels. Not available for purchase.','operations':[]},
]

