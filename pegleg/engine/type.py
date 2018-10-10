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

from prettytable import PrettyTable

from pegleg.engine import util

__all__ = ('list_types', )

LOG = logging.getLogger(__name__)


def list_types(output_stream):
    """List type names for a given repository."""

    # Create a table to output site types for a given repo
    type_table = PrettyTable()
    type_table.field_names = ['type_name']
    for type_name in util.files.list_types():
        type_table.add_row([type_name])
    # Write table to specified output_stream
    output_stream.write(type_table.get_string() + "\n")
