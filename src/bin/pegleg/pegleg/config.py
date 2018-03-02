from copy import copy

try:
    if GLOBAL_CONTEXT:
        pass
except NameError:
    GLOBAL_CONTEXT = {
        'primary_repo': './',
        'aux_repos': [],
    }


def get_primary_repo():
    return GLOBAL_CONTEXT['primary_repo']


def set_primary_repo(r):
    GLOBAL_CONTEXT['primary_repo'] = r


def set_auxiliary_repo_list(a):
    GLOBAL_CONTEXT['aux_repos'] = copy(a)


def add_auxiliary_repo(a):
    GLOBAL_CONTEXT['aux_repos'].append(a)


def get_auxiliary_repo_list():
    return GLOBAL_CONTEXT['aux_repos']


def each_auxiliary_repo():
    for a in GLOBAL_CONTEXT['aux_repos']:
        yield a


def all_repos():
    repos = [get_primary_repo()]
    repos.extend(get_auxiliary_repo_list())
    return repos
