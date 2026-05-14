from recipe_quality.ai_annotation import OpenAIAnnotationClient, OpenAIAnnotationConfig
from recipe_quality.fatsecret.client import FatSecretClient, FatSecretConfig


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
