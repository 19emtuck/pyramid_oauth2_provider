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
import json

from sqlalchemy import engine_from_config
import transaction

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    Base,
    get_engine,
    get_session_factory,
    get_tm_session,
    )

def usage(argv):
    cmd = os.path.basename(argv[0])
    print(('usage: %s <config_uri> <drop>\n'
          '(example: "%s development.ini false")' % (cmd, cmd)))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)

    config_uri = argv[1]
    drop = json.loads(argv[2].lower())
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')

    session_factory = get_session_factory(engine)
    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)

        if drop:
            Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
