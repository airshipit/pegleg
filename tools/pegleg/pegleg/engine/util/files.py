import click
import os
import yaml

__all__ = [
    'all',
    'create_global_directories',
    'create_site_directories',
    'create_site_type_directories',
    'directories_for',
    'directory_for',
    'dump',
    'existing_directories',
    'search',
    'slurp',
]

DIR_DEPTHS = {
    'global': 1,
    'type': 2,
    'site': 1,
}


def all():
    return search(DIR_DEPTHS.keys())


def create_global_directories(aic_revision):
    _create_tree(_global_common_path())
    _create_tree(_global_revision_path(aic_revision))


def create_site_directories(*, site_name, aic_revision, **_kwargs):
    _create_tree(_site_path(site_name))


def create_site_type_directories(*, aic_revision, site_type):
    _create_tree(_site_type_common_path(site_type))
    _create_tree(_site_type_revision_path(site_type, aic_revision))


FULL_STRUCTURE = {
    'directories': {
        'baremetal': {},
        'networks': {
            'directories': {
                'physical': {},
            },
        },
        'pki': {},
        'profiles': {
            'directories': {
                'hardware': {},
                'host': {},
            }
        },
        'schemas': {},
        'secrets': {
            'directories': {
                'certificate-authorities': {},
                'certificates': {},
                'keypairs': {},
                'passphrases': {},
            },
        },
        'software': {
            'directories': {
                'charts': {},
                'config': {},
                'manifests': {},
            },
        },
    },
}


def _create_tree(root_path, *, tree=FULL_STRUCTURE):
    for name, data in tree.get('directories', {}).items():
        path = os.path.join(root_path, name)
        os.makedirs(path, mode=0o775, exist_ok=True)
        _create_tree(path, tree=data)


def directories_for(*, site_name, aic_revision, site_type):
    return [
        _global_common_path(),
        _global_revision_path(aic_revision),
        _site_type_common_path(site_type),
        _site_type_revision_path(site_type, aic_revision),
        _site_path(site_name),
    ]


def _global_common_path():
    return 'global/common'


def _global_revision_path(aic_revision):
    return 'global/%s' % aic_revision


def _site_type_common_path(site_type):
    return 'type/%s/common' % site_type


def _site_type_revision_path(site_type, aic_revision):
    return 'type/%s/%s' % (site_type, aic_revision)


def _site_path(site_name):
    return 'site/%s' % site_name


def list_sites():
    for path in os.listdir('site'):
        joined_path = os.path.join('site', path)
        if os.path.isdir(joined_path):
            yield path


def directory_for(*, path):
    parts = os.path.normpath(path).split(os.sep)
    depth = DIR_DEPTHS.get(parts[0])
    if depth is not None:
        return os.path.join(*parts[:depth + 1])


def existing_directories():
    directories = set()
    for search_path, depth in DIR_DEPTHS.items():
        directories.update(_recurse_subdirs(search_path, depth))
    return directories


def slurp(path):
    if not os.path.exists(path):
        raise click.ClickException(
            '%s not found.  pegleg must be run from '
            'the root of an AIC cLCP configuration repostiory.' % path)

    with open(path) as f:
        try:
            return yaml.load(f)
        except Exception as e:
            raise click.ClickException('Failed to parse %s:\n%s' % (path, e))


def dump(path, data):
    if os.path.exists(path):
        raise click.ClickException('%s already exists, aborting' % path)

    os.makedirs(os.path.dirname(path), mode=0o775, exist_ok=True)

    with open(path, 'w') as f:
        yaml.dump(data, f, explicit_start=True)


def _recurse_subdirs(search_path, depth):
    directories = set()
    for path in os.listdir(search_path):
        joined_path = os.path.join(search_path, path)
        if os.path.isdir(joined_path):
            if depth == 1:
                directories.add(joined_path)
            else:
                directories.update(_recurse_subdirs(joined_path, depth - 1))
    return directories


def search(search_paths):
    for search_path in search_paths:
        for root, _dirs, filenames in os.walk(search_path):
            for filename in filenames:
                yield os.path.join(root, filename)
