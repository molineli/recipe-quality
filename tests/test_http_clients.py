import pytest

from recipe_quality.ai_annotation import OpenAIAnnotationClient, OpenAIAnnotationConfig
from recipe_quality.fatsecret.client import FatSecretClient, FatSecretConfig, FatSecretError


class FatSecretTimeoutSession:
    trust_env = True

    def __init__(self):
        self.last_timeout = None

    def get(self, *args, **kwargs):
        from requests import ReadTimeout

        self.last_timeout = kwargs.get("timeout")
        raise ReadTimeout("read timed out")


class FatSecretFailingSession:
    trust_env = True

    def __init__(self, exc):
        self.exc = exc

    def get(self, *args, **kwargs):
        raise self.exc


def test_openai_annotation_client_ignores_environment_proxies_by_default():
    client = OpenAIAnnotationClient(
        config=OpenAIAnnotationConfig(api_key="test-key"),
    )

    assert client.session.trust_env is False


def test_fatsecret_client_ignores_environment_proxies_by_default():
    client = FatSecretClient(
        config=FatSecretConfig(client_id="test-id", client_secret="test-secret"),
    )

    assert client.session.trust_env is False


def test_fatsecret_client_configures_retries_for_transient_status_codes():
    client = FatSecretClient(
        config=FatSecretConfig(client_id="test-id", client_secret="test-secret"),
    )

    adapter = client.session.adapters["https://"]
    retries = adapter.max_retries

    assert set(retries.status_forcelist) == {429, 500, 502, 503, 504}
    assert retries.total == 3


def test_fatsecret_client_translates_read_timeout_to_runtime_error():
    session = FatSecretTimeoutSession()
    client = FatSecretClient(
        config=FatSecretConfig(client_id="test-id", client_secret="test-secret"),
        session=session,
    )
    client._access_token = "token"
    client._token_expires_at = 9999999999

    try:
        client.search_foods("rice")
    except FatSecretError as exc:
        assert "FatSecret API request timed out while reading the response" in str(exc)
    else:
        raise AssertionError("Expected FatSecretError")

    assert session.last_timeout == (5, 40)


@pytest.mark.parametrize(
    ("exception_name", "expected_message"),
    [
        ("ConnectTimeout", "timed out while connecting"),
        ("HTTPError", "failed with an HTTP error"),
        ("RequestException", "failed due to a network error"),
    ],
)
def test_fatsecret_client_translates_request_exceptions_to_runtime_error(
    exception_name,
    expected_message,
):
    import requests

    exc = getattr(requests, exception_name)("temporary failure")
    client = FatSecretClient(
        config=FatSecretConfig(client_id="test-id", client_secret="test-secret"),
        session=FatSecretFailingSession(exc),
    )
    client._access_token = "token"
    client._token_expires_at = 9999999999

    with pytest.raises(FatSecretError, match=expected_message):
        client.search_foods("rice")
