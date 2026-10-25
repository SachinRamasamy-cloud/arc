"""Approved typed linear processing graph contract; no IO or framework state."""
from foundation.errors.public import PublicError
from modules.service_catalog.public import OPERATIONS

def validate_graph(graph):
    """Launch supports a bounded typed linear DAG; no arbitrary expressions or code."""
    if not isinstance(graph,dict) or set(graph)-{'nodes','edges'}: raise PublicError('WORKFLOW_INVALID')
    nodes=graph.get('nodes',[]);edges=graph.get('edges',[])
    if not isinstance(nodes,list) or not 3<=len(nodes)<=10 or not isinstance(edges,list): raise PublicError('WORKFLOW_INVALID')
    ids={}; incoming={};outgoing={}
    for node in nodes:
        if not isinstance(node,dict) or not isinstance(node.get('id'),str) or len(node['id'])>64 or node['id'] in ids: raise PublicError('WORKFLOW_INVALID')
        kind=node.get('data',{}).get('kind')
        if kind not in ('input','output',*OPERATIONS): raise PublicError('WORKFLOW_INVALID')
        ids[node['id']]=node
        incoming[node['id']]=[];outgoing[node['id']]=[]
    for edge in edges:
        a,b=edge.get('source'),edge.get('target')
        if a not in ids or b not in ids or a==b: raise PublicError('WORKFLOW_INVALID')
        outgoing[a].append(b);incoming[b].append(a)
    starts=[n for n in ids if ids[n]['data']['kind']=='input']
    ends=[n for n in ids if ids[n]['data']['kind']=='output']
    if len(starts)!=1 or len(ends)!=1 or len(edges)!=len(nodes)-1: raise PublicError('WORKFLOW_INVALID')
    ordered=[];current=starts[0];visited=set();data_type='json'
    while True:
        if current in visited: raise PublicError('WORKFLOW_INVALID')
        visited.add(current);node=ids[current];kind=node['data']['kind']
        if len(incoming[current])!=(0 if kind=='input' else 1): raise PublicError('WORKFLOW_INVALID')
        if kind=='output':
            if outgoing[current]: raise PublicError('WORKFLOW_INVALID')
            break
        if len(outgoing[current])!=1: raise PublicError('WORKFLOW_INVALID')
        if kind=='input':
            data_type=node['data'].get('format','json')
            if data_type not in ('json','csv'): raise PublicError('WORKFLOW_INVALID')
        else:
            if kind=='csv_to_json' and data_type!='csv': raise PublicError('WORKFLOW_INVALID')
            if kind!='csv_to_json' and data_type!='json': raise PublicError('WORKFLOW_INVALID')
            data_type='csv' if kind=='json_to_csv' else 'json'
            config=node['data'].get('config',{})
            if not isinstance(config,dict) or set(config)-{'required_fields','mappings','lowercase'}: raise PublicError('WORKFLOW_INVALID')
            ordered.append({'node_id':current,'operation':kind,**config})
        current=outgoing[current][0]
    if len(visited)!=len(nodes) or not ordered: raise PublicError('WORKFLOW_INVALID')
    return ordered

