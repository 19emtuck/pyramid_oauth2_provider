#
# Copyright (c) Elliot Peele <elliot@bentlogic.net>
#
# This program is distributed under the terms of the MIT License as found
# in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/mit-license.php.
#
# This program is distributed in the hope that it will be useful, but
# without any warrenty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the MIT License for full details.
#

from sqlalchemy import engine_from_config

from pyramid.config import Configurator
from pyramid.exceptions import ConfigurationError
from pyramid.interfaces import IAuthenticationPolicy

from pyramid.authorization import ACLAuthorizationPolicy

from .interfaces import IAuthCheck
from .authentication import OauthAuthenticationPolicy

# imported to make the test runnner happy
from . import tests

def includeme(config):
    settings = config.registry.settings

    config.include('.models')

    # Security policies
    # a default authorization policy is mandatory
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)

    if not config.registry.queryUtility(IAuthenticationPolicy):
        config.set_authentication_policy(OauthAuthenticationPolicy())

    auth_check = settings.get('oauth2_provider.auth_checker')
    if not auth_check:
        raise ConfigurationError('You must provide an implementation of the '
            'authentication check interface that is included with '
            'pyramid_oauth2_provider for verifying usernames and passwords')

    policy = config.maybe_dotted(auth_check)
    config.registry.registerUtility(policy, IAuthCheck)

    config.add_route('oauth2_provider_authorize', '/oauth2/authorize')
    config.add_route('oauth2_provider_token', '/oauth2/token')
    config.scan()

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, root_factory='pyramid_oauth2_provider.security.RootFactory')
    includeme(config)
    return config.make_wsgi_app()
