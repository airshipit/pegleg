from pegleg.engine import util

__all__ = ['global_', 'site', 'site_type']


def global_(revision):
    util.files.create_global_directories(revision)


def site(revision, site_type, site_name):
    util.definition.create(
        revision=revision, site_name=site_name, site_type=site_type)
    params = util.definition.load_as_params(site_name)
    util.files.create_site_directories(**params)


def site_type(revision, site_type):
    util.files.create_site_type_directories(
        revision=revision, site_type=site_type)
