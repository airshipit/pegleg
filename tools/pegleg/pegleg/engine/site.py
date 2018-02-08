from pegleg.engine import util
import collections
import csv
import json

__all__ = ['collect', 'impacted', 'list_', 'show']


def collect(site_name, output_stream):
    for filename in util.definition.site_files(site_name):
        with open(filename) as f:
            output_stream.writelines(f.readlines())


def impacted(input_stream, output_stream):
    mapping = _build_impact_mapping()
    impacted_sites = set()

    for line in input_stream:
        line = line.strip()
        directory = util.files.directory_for(path=line)
        if directory is not None:
            impacted_sites.update(mapping[directory])

    for site_name in sorted(impacted_sites):
        output_stream.write(site_name + '\n')


def list_(output_stream):
    fieldnames = ['site_name', 'site_type', 'revision']
    writer = csv.DictWriter(
        output_stream, fieldnames=fieldnames, delimiter=' ')
    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name)
        writer.writerow(params)


def show(site_name, output_stream):
    data = util.definition.load_as_params(site_name)
    data['files'] = list(util.definition.site_files(site_name))
    json.dump(data, output_stream, indent=2, sort_keys=True)


def _build_impact_mapping():
    mapping = collections.defaultdict(set)

    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name)
        for directory in util.files.directories_for(**params):
            mapping[directory].add(site_name)

    return mapping
