from setuptools import setup, find_packages

setup(
    name='collective.taskqueue',
    version='0.4.3',
    description='',
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGES.txt').read()),
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Programming Language :: Python',
    ],
    keywords='',
    author='Asko Soukka',
    author_email='asko.soukka@iki.fi',
    url='https://github.com/datakurre/collective.taskqueue/',
    license='GPL',
    packages=find_packages('src', exclude=['ez_setup']),
    package_dir={'': 'src'},
    namespace_packages=['collective'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'Zope2',
        'five.globalrequest',
    ],
    extras_require={
        'test': ['plone.app.testing', 'plone.app.robotframework>=0.7.0rc4'],
        'redis': ['redis>=2.4.10', 'msgpack-python']
    },
    entry_points='''
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone
    '''
)
