import pytest
from foundation.errors.public import PublicError
from modules.payments.domain.checkout_policy import checkout_request_key

def test_checkout_key_is_workspace_scoped_and_repeatable():
    assert checkout_request_key('wA','same')==checkout_request_key('wA','same')
    assert checkout_request_key('wA','same')!=checkout_request_key('wB','same')
    assert len(checkout_request_key('wA','same'))==64

@pytest.mark.parametrize('key',['','a'*129])
def test_checkout_key_rejects_missing_and_too_long_values(key):
    with pytest.raises(PublicError):checkout_request_key('wA',key)
