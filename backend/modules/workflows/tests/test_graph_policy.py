import pytest
from foundation.errors.public import PublicError
from modules.workflows.domain.graph_policy import validate_graph

def test_graph_policy_accepts_one_approved_processing_step():
    graph={'nodes':[{'id':'input','data':{'kind':'input','format':'json'}},{'id':'clean','data':{'kind':'normalize','config':{'lowercase':['email']}}},{'id':'output','data':{'kind':'output'}}],'edges':[{'source':'input','target':'clean'},{'source':'clean','target':'output'}]}
    assert validate_graph(graph)==[{'node_id':'clean','operation':'normalize','lowercase':['email']}]

def test_graph_policy_rejects_unknown_code_node():
    graph={'nodes':[{'id':'input','data':{'kind':'input','format':'json'}},{'id':'bad','data':{'kind':'python'}},{'id':'output','data':{'kind':'output'}}],'edges':[{'source':'input','target':'bad'},{'source':'bad','target':'output'}]}
    with pytest.raises(PublicError):validate_graph(graph)
