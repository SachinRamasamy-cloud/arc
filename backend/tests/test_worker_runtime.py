import pytest
from entrypoints.worker_runtime import run_loop

@pytest.mark.parametrize('value',[-1,0])
def test_worker_rejects_invalid_intervals(value):
    with pytest.raises(ValueError): run_loop(lambda: False,idle_seconds=value)

@pytest.mark.parametrize('value',[-1,0])
def test_worker_rejects_invalid_periodic_intervals(value):
    with pytest.raises(ValueError):run_loop(lambda: False,periodic_seconds=value)
