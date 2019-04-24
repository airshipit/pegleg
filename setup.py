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

from setuptools import setup
from setuptools import find_packages

setup(
    name='pegleg',
    python_requires='>=3.5.0',
    version='0.1.0',
    description=('Pegleg is a document aggregator that provides early '
                 'linting and validations via Deckhand, a document '
                 'management micro-service within Airship.'),
    url='https://opendev.org/airship/pegleg',
    author='The Airship Authors',
    license='Apache 2.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pegleg=pegleg.cli:main',
    ]},
    include_package_data=True,
    package_dir={'pegleg': 'pegleg'},
    package_data={
        'pegleg': [
            'schemas/*.yaml',
        ],
    },
)
