import asyncio
import pytest

from utils.error_handler import handle_agent_errors


class DummyRateLimitError(Exception):
    pass


async def failing_task(attempts, fail_times=2):
    if attempts['count'] < fail_times:
        attempts['count'] += 1
        raise DummyRateLimitError('Rate limit exceeded')
    return 'success'


@handle_agent_errors(max_retries=3, context='測試', show_progress=False)
async def sample_agent(attempts):
    return await failing_task(attempts)


def test_handle_agent_errors_retry():
    attempts = {'count': 0}
    result = asyncio.run(sample_agent(attempts))
    assert result == 'success'
    assert attempts['count'] == 2


@handle_agent_errors(max_retries=1, context='測試', show_progress=False)
async def always_fail():
    raise DummyRateLimitError('Rate limit exceeded')


def test_handle_agent_errors_failure():
    with pytest.raises(DummyRateLimitError):
        asyncio.run(always_fail())
