from types import SimpleNamespace
from modules.wallets.application.use_cases import wallet_dict

def test_wallet_breakdown_does_not_double_count_reserved_credits():
    value=SimpleNamespace(balance_milli=10_000,held_milli=2_500,spent_milli=3_000,environment='live',frozen=False)
    assert wallet_dict(value)=={'balance_milli':10_000,'reserved_milli':2_500,'available_milli':7_500,'spent_milli':3_000,'environment':'live','frozen':False}
