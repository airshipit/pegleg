# Copyright 2018 AT&T Intellectual Property.  All other rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

__all__ = (
    'PeglegBaseException', 'GitException', 'GitAuthException',
    'GitProxyException', 'GitSSHException', 'GitConfigException',
    'GitInvalidRepoException')

LOG = logging.getLogger(__name__)


class PeglegBaseException(Exception):
    """The base Pegleg exception for everything."""

    message = "Base Pegleg exception"

    def __init__(self, message=None, **kwargs):
        self.message = message or self.message
        try:
            self.message = self.message.format(**kwargs)
        except KeyError:
            LOG.warning("Missing kwargs")
        super().__init__(self.message)


class GitException(PeglegBaseException):
    """Exception when an error occurs cloning a Git repository."""
    message = (
        'Git exception occurred: [%(location)s] may not be a valid '
        'git repository. Details: %(details)s')


class GitAuthException(PeglegBaseException):
    """Exception that occurs when authentication fails for cloning a repo."""
    message = (
        'Failed to authenticate for repo %(repo_url)s with ssh-key '
        'at path %(ssh_key_path)s')


class GitProxyException(PeglegBaseException):
    """Exception when cloning through proxy."""
    message = 'Could not resolve proxy [%(location)s]'


class GitSSHException(PeglegBaseException):
    """Exception that occurs when an SSH key could not be found."""
    message = 'Failed to find specified SSH key: %(ssh_key_path)s'


class GitConfigException(PeglegBaseException):
    """Exception that occurs when reading Git repo config fails."""
    message = 'Failed to read Git config file for repo path: %(repo_url)s'


class GitInvalidRepoException(PeglegBaseException):
    """Exception raised when an invalid repository is detected."""
    message = 'The repository path or URL is invalid: %(repo_url)s'


class GitMissingUserException(PeglegBaseException):
    """Exception raised when a username is required, but not provided."""
    message = 'Repo URL %(url)s requires a username, but none was provided.'


#
# PKI EXCEPTIONS
#


class IncompletePKIPairError(PeglegBaseException):
    """Exception for incomplete private/public keypair."""
    message = ("Incomplete keypair set %(kinds)s for name: %(name)s")


class PassphraseCatalogNotFoundException(PeglegBaseException):
    """Failed to find Catalog for Passphrases generation."""
    message = (
        'Could not find the Passphrase Catalog to generate '
        'the site Passphrases!')


class InvalidPassphraseType(PeglegBaseException):
    """Invalid Passphrase type"""
    message = (
        'Invalid Passphrase type %(ptype)s specified for %(pname)s. Valid '
        'values are: %(validvalues)s.')


class InvalidPassphrasePrompt(PeglegBaseException):
    """Invalid Passphrase prompt field"""
    message = (
        'Invalid Passphrase prompt %(pprompt)s specified for %(pname)s. Valid '
        'values are: %(validvalues)s.')


class InvalidPassphraseRegeneration(PeglegBaseException):
    """Invalid Regenerable value for entry in passphrase-catalog"""
    message = (
        'Invalid Regenerable value %(pregen)s specified for %(pname)s. Valid '
        'values are: %(validvalues)s.')


class GenesisBundleEncryptionException(PeglegBaseException):
    """Exception raised when encryption of the genesis bundle fails."""

    message = 'Encryption is required for genesis bundle, but no encryption ' \
              'policy or key is specified.'


class GenesisBundleGenerateException(PeglegBaseException):
    """
    Exception raised when pormenade engine fails to build the genesis
    bundle.
    """

    message = 'Bundle generation failed on deckhand validation.'


class PKICertificateInvalidDuration(PeglegBaseException):
    """Exception for invalid duration of PKI Certificate."""
    message = (
        'Provided duration is invalid. Certificate durations must be '
        'a positive integer.')


#
# CREDENTIALS EXCEPTIONS
#


class PassphraseNotFoundException(PeglegBaseException):
    """Exception raised when passphrase is not set."""

    message = 'PEGLEG_PASSPHRASE must be set'


class PassphraseInsufficientLengthException(PeglegBaseException):
    """Exception raised when passphrase is too short."""

    message = 'PEGLEG_PASSPHRASE must be at least 24 characters long.'


class SaltNotFoundException(PeglegBaseException):
    """Exception raised when salt is not set."""

    message = 'PEGLEG_SALT must be set'


class SaltInsufficientLengthException(PeglegBaseException):
    """Exception raised when salt is too short."""

    message = 'PEGLEG_SALT must be at least 24 characters long.'


class GlobalCredentialsNotFound(PeglegBaseException):
    """Exception raised when global_passphrase or global_salt are not found."""

    message = (
        'global_salt and global_passphrase must either both be '
        'defined, or neither can be defined in site documents.')


#
# Shipyard Helper Exceptions
#


class InvalidBufferModeException(PeglegBaseException):
    """Exception raised when invalid buffer mode specified"""

    message = 'BUFFER MODE must be one of: append, auto, replace'
