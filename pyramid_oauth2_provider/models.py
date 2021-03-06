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

import time
from datetime import datetime
from base64 import b64decode

from sqlalchemy import Column
from sqlalchemy import ForeignKey

from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Unicode
from sqlalchemy import engine_from_config

from sqlalchemy.ext.declarative import declarative_base
import zope.sqlalchemy

from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import synonym

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from .util import oauth2_settings

from .generators import gen_token
from .generators import gen_client_id
from .generators import gen_client_secret

Base = declarative_base()
backend = default_backend()


class Oauth2Client(Base):
    __tablename__ = 'oauth2_provider_clients'
    id = Column(Integer, primary_key=True)
    client_id = Column(Unicode(64), unique=True, nullable=False)
    _client_secret = Column(LargeBinary(length=255), nullable=False)
    revoked = Column(Boolean, default=False)
    revocation_date = Column(DateTime)
    _salt = None

    def __init__(self, salt=None):
        self._salt = salt
        self.client_id = gen_client_id()
        self.client_secret = gen_client_secret()

    def new_client_secret(self):
        secret = gen_client_secret()
        self.client_secret = secret
        return secret

    def _get_client_secret(self):
        return self._client_secret

    def _set_client_secret(self, client_secret):
        if self._salt:
            salt = b64decode(self._salt.encode('utf-8'))
        else:
            try:
                if not oauth2_settings('salt'):
                    raise ValueError(
                        'oauth2_provider.salt configuration required.'
                    )
                salt = b64decode(oauth2_settings('salt').encode('utf-8'))
            except AttributeError:
                return

        kdf = Scrypt(
            salt=salt,
            length=64,
            n=2 ** 14,
            r=8,
            p=1,
            backend=backend
        )

        try:
            client_secret = bytes(client_secret, 'utf-8')
        except TypeError:
            pass
        self._client_secret = kdf.derive(client_secret)

    client_secret = synonym('_client_secret', descriptor=property(
        _get_client_secret, _set_client_secret))

    def revoke(self):
        self.revoked = True
        self.revocation_date = datetime.utcnow()

    def isRevoked(self):
        return self.revoked


class Oauth2RedirectUri(Base):
    __tablename__ = 'oauth2_provider_redirect_uris'
    id = Column(Integer, primary_key=True)
    uri = Column(Unicode(256), unique=True, nullable=False)

    client_id = Column(Integer, ForeignKey(Oauth2Client.id))
    client = relationship(Oauth2Client, backref=backref('redirect_uris'))

    def __init__(self, client, uri):
        self.client = client
        self.uri = uri


class Oauth2Code(Base):
    __tablename__ = 'oauth2_provider_codes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    authcode = Column(Unicode(64), unique=True, nullable=False)
    expires_in = Column(Integer, nullable=False, default=10*60)

    revoked = Column(Boolean, default=False)
    revocation_date = Column(DateTime)

    creation_date = Column(DateTime, default=datetime.utcnow)

    client_id = Column(Integer, ForeignKey(Oauth2Client.id))
    client = relationship(Oauth2Client, backref=backref('authcode'))

    def __init__(self, client, user_id):
        self.client = client
        self.user_id = user_id

        self.authcode = gen_token(self.client)

    def revoke(self):
        self.revoked = True
        self.revocation_date = datetime.utcnow()

    def isRevoked(self):
        expiry = time.mktime(self.create_date.timetuple()) + self.expires_in
        if datetime.frometimestamp(expiry) < datetime.utcnow():
            self.revoke()
        return self.revoked


class Oauth2Token(Base):
    __tablename__ = 'oauth2_provider_tokens'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    access_token = Column(Unicode(64), unique=True, nullable=False)
    refresh_token = Column(Unicode(64), unique=True, nullable=False)
    expires_in = Column(Integer, nullable=False, default=60*60)

    revoked = Column(Boolean, default=False)
    revocation_date = Column(DateTime)

    creation_date = Column(DateTime, default=datetime.utcnow)

    client_id = Column(Integer, ForeignKey(Oauth2Client.id))
    client = relationship(Oauth2Client, backref=backref('tokens'))

    def __init__(self, client, user_id):
        self.client = client
        self.user_id = user_id

        self.access_token = gen_token(self.client)
        self.refresh_token = gen_token(self.client)

    def revoke(self):
        self.revoked = True
        self.revocation_date = datetime.utcnow()

    def isRevoked(self):
        expiry = time.mktime(self.creation_date.timetuple()) + self.expires_in
        if datetime.fromtimestamp(expiry) < datetime.utcnow():
            self.revoke()
        return self.revoked

    def refresh(self):
        """
        Generate a new token for this client.
        """

        cls = self.__class__
        self.revoke()
        return cls(self.client, self.user_id)

    def asJSON(self, **kwargs):
        token = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'user_id': self.user_id,
            'expires_in': self.expires_in,
        }
        kwargs.update(token)
        return kwargs


def get_engine(settings, prefix='sqlalchemy.'):
    return engine_from_config(settings, prefix)


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    return factory


def get_tm_session(session_factory, transaction_manager):
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    This function will hook the session to the transaction manager which
    will take care of committing any changes.

    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.

    - When using scripts you should wrap the session in a manager yourself.
      For example::

          import transaction

          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              dbsession = get_tm_session(session_factory, transaction.manager)

    """
    dbsession = session_factory()
    zope.sqlalchemy.register(dbsession,
                             transaction_manager=transaction_manager)
    return dbsession

def includeme(config):
    """
    Initialize the model for a Pyramid app.

    Activate this setup using ``config.include('test_alch.models')``.

    """
    settings = config.get_settings()
    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include('pyramid_tm')

    session_factory = get_session_factory(get_engine(settings))
    config.registry['dbsession_factory'] = session_factory

    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        # r.tm is the transaction manager used by pyramid_tm
        lambda r: get_tm_session(session_factory, r.tm),
        'dbsession',
        reify=True)
