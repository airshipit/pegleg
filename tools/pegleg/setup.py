from setuptools import setup

setup(
    name='pegleg',
    version='0.1.0',
    packages=['pegleg'],
    entry_points={
        'console_scripts': [
            'pegleg=pegleg.cli:main',
    ]},
    include_package_data=True,
    package_data={
        'schemas': [
            'schemas/*.yaml',
        ],
    },
)
