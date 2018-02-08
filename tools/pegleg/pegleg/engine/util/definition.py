from . import files
import click

__all__ = [
    'create',
    'load',
    'load_as_params',
    'path',
    'pluck',
    'site_files',
]


def create(*, site_name, site_type, revision):
    definition = {
        'schema': 'pegleg/SiteDefinition/v1',
        'metadata': {
            'schema': 'metadata/Document/v1',
            'name': site_name,
            'storagePolicy': 'cleartext',
            'layeringDefinition': {
                'abstract': False,
                'layer': 'site',
            },
        },
        'data': {
            'revision': revision,
            'site_type': site_type,
        }
    }
    files.dump(path(site_name), definition)


def load(site):
    return files.slurp(path(site))


def load_as_params(site_name):
    definition = load(site_name)
    params = definition.get('data', {})
    params['site_name'] = site_name
    return params


def path(site_name):
    return 'site/%s/site-definition.yaml' % site_name


def pluck(site_definition, key):
    try:
        return site_definition['data'][key]
    except Exception as e:
        site_name = site_definition.get('metadata', {}).get('name')
        raise click.ClickException(
            'failed to get "%s" from site  definition "%s": %s' (key,
                                                                 site_name, e))


def site_files(site_name):
    params = load_as_params(site_name)
    for filename in files.search(files.directories_for(**params)):
        yield filename
    yield path(site_name)
