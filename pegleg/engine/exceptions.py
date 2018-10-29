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


class PeglegBaseException(Exception):
    """Base class for Pegleg exception and error handling."""

    def __init__(self, message=None, **kwargs):
        self.message = message or self.message
        try:  # nosec
            self.message = self.message % kwargs
        except Exception:
            pass
        super(PeglegBaseException, self).__init__(self.message)


class BaseGitException(PeglegBaseException):
    """Base class for Git exceptions and error handling."""

    message = 'An unknown error occurred while accessing a chart source.'


class GitException(BaseGitException):
    """Exception when an error occurs cloning a Git repository."""

    def __init__(self, location, details=None):
        self._message = ('Git exception occurred: [%s] may not be a valid git '
                         'repository' % location)
        if details:
            self._message += '. Details: %s' % details

        super(GitException, self).__init__(self._message)


class GitAuthException(BaseGitException):
    """Exception that occurs when authentication fails for cloning a repo."""

    def __init__(self, repo_url, ssh_key_path):
        self._repo_url = repo_url
        self._ssh_key_path = ssh_key_path

        self._message = ('Failed to authenticate for repo %s with ssh-key at '
                         'path %s' % (self._repo_url, self._ssh_key_path))

        super(GitAuthException, self).__init__(self._message)


class GitProxyException(BaseGitException):
    """Exception when an error occurs cloning a Git repository
       through a proxy."""

    def __init__(self, location):
        self._location = location
        self._message = ('Could not resolve proxy [%s]' % self._location)

        super(GitProxyException, self).__init__(self._message)


class GitSSHException(BaseGitException):
    """Exception that occurs when an SSH key could not be found."""

    def __init__(self, ssh_key_path):
        self._ssh_key_path = ssh_key_path

        self._message = ('Failed to find specified SSH key: %s' %
                         (self._ssh_key_path))

        super(GitSSHException, self).__init__(self._message)


class GitConfigException(BaseGitException):
    """Exception that occurs when reading Git repo config fails."""
    message = ("Failed to read Git config file for repo path: %(repo_path)s")


class GitInvalidRepoException(BaseGitException):
    """Exception raised when an invalid repository is detected."""
    message = ("The repository path or URL is invalid: %(repo_path)s")
