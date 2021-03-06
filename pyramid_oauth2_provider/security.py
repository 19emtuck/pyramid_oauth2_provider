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

from pyramid.security import (
    Allow,
    Everyone,
    Authenticated,
)

class RootFactory(object):
    """
    The default root factory.
    """

    __acl__ = [ (Allow, Authenticated, 'system.Authenticated') ]

    def __init__(self, request):
        """
        """
        pass
