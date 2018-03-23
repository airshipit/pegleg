import click

from pegleg import config
from . import files

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


def load(site, primary_repo_base=None):
    return files.slurp(path(site, primary_repo_base))


def load_as_params(site_name, primary_repo_base=None):
    definition = load(site_name, primary_repo_base)
    params = definition.get('data', {})
    params['site_name'] = site_name
    return params


def path(site_name, primary_repo_base=None):
    if not primary_repo_base:
        primary_repo_base = config.get_primary_repo()
    return '%s/site/%s/site-definition.yaml' % (primary_repo_base, site_name)


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


def site_files_by_repo(site_name):
    """Yield tuples of repo_base, file_name."""
    params = load_as_params(site_name)
    dir_map = files.directories_for_each_repo(**params)
    for repo, dl in dir_map.items():
        for filename in files.search(dl):
            yield (repo, filename)
