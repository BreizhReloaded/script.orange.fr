# -*- coding: utf-8 -*-
"""List all available providers and return the provider selected by the user"""
from lib.utils import get_addon_setting, log, LogLevel

from .provider_interface import ProviderInterface
from .fr import FreeProvider, OrangeFranceProvider

_PROVIDERS = {
    'France.Free': FreeProvider,
    'France.Orange': OrangeFranceProvider
}

_KEY = '{country}.{name}'.format(
    country=get_addon_setting('provider.country'),
    name=get_addon_setting('provider.name')
)

_PROVIDER = _PROVIDERS[_KEY]() if _PROVIDERS.get(_KEY) is not None else None

if not _PROVIDER:
    log('Cannot instanciate provider: {}'.format(_KEY), LogLevel.ERROR)

def get_provider() -> ProviderInterface:
    """Return the selected provider"""
    return _PROVIDER
