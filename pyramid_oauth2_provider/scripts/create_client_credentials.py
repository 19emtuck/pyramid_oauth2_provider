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

import os
import sys

import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid_oauth2_provider.models import (
    Oauth2Client,
    get_session_factory,
    get_tm_session
    )

def create_client(dbsession, salt=None):
    client = Oauth2Client(salt=salt)
    client_secret = client.new_client_secret()
    dbsession.add(client)
    return client.client_id, client_secret

def usage(argv):
    cmd = os.path.basename(argv[0])
    print(('usage: %s <config_uri> <section>\n'
          '(example: "%s development.ini myproject")' % (cmd, cmd)))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)
    config_uri = argv[1]
    section = argv[2]
    setup_logging(config_uri)

    print("loading configuration section", section)
    settings = get_appsettings(config_uri, section)
    engine = engine_from_config(settings, 'sqlalchemy.')
    try:
        salt = settings['oauth2_provider.salt']
    except KeyError:
        raise ValueError(
            'oauth2_provider.salt configuration required.'
        )

    session_factory = get_session_factory(engine)
    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        id, secret = create_client(dbsession, salt=salt)
        print('client_id:', id)
        print('client_secret:', secret)

if __name__ == '__main__':
    main()
