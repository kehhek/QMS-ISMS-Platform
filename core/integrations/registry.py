from .aws import AWSProvider
from .github import GitHubProvider

PROVIDERS = {
    'github': GitHubProvider(),
    'aws': AWSProvider(),
}


def get_provider(provider_key):
    provider = PROVIDERS.get(provider_key)
    if not provider:
        raise ValueError(f'Unknown integration provider: {provider_key}')
    return provider
