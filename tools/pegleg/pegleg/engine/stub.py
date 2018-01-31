from pegleg.engine import util

__all__ = ['global_', 'site', 'site_type']


def global_(aic_revision):
    util.files.create_global_directories(aic_revision)


def site(aic_revision, site_type, site_name):
    util.definition.create(
        aic_revision=aic_revision, site_name=site_name, site_type=site_type)
    params = util.definition.load_as_params(site_name)
    util.files.create_site_directories(**params)


def site_type(aic_revision, site_type):
    util.files.create_site_type_directories(
        aic_revision=aic_revision, site_type=site_type)
