from types import SimpleNamespace
from modules.pricing.domain.units import quote_cost

def test_quote_cost_uses_kib_ceiling_and_node_count():
    settings=SimpleNamespace(processing_base_milli=500,processing_kib_milli=100)
    assert quote_cost(1,steps=1,settings=settings)==600
    assert quote_cost(1025,steps=2,settings=settings)==1400
