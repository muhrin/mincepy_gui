# -*- coding: utf-8 -*-
from setuptools import setup

__author__ = "Martin Uhrin"
__license__ = "GPLv3 and MIT"
__contributors__ = "Sonia Collaud"

about = {}
with open('mincepy_gui/version.py') as f:
    exec(f.read(), about)

setup(
    name='mincepy-gui',
    version=about['__version__'],
    description="GUI for navigating your mincepy database visually!",
    long_description=open('README.rst').read(),
    url='https://github.com/muhrin/mincepy_gui.git',
    author='Martin Uhrin',
    author_email='martin.uhrin.10@ucl.ac.uk',
    license=__license__,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='database schemaless nosql object-store gui',
    install_requires=[
        'mincepy>=0.15.8',
        'PySide2',
        'pytray>=0.2.2',
        'stevedore',
    ],
    extras_require={
        'gui': [],
        'dev': [
            'pip',
            'pytest>4',
            'pytest-cov',
            'pytest-qt',
            'pre-commit',
            'yapf',
            'prospector',
            'pylint',
            'twine',
        ],
    },
    packages=['mincepy_gui'],
    include_package_data=True,
    test_suite='test',
    provides=[],
    entry_points={'mincepy_gui.actioners': ['native_types = mincepy_gui.actioners:get_actioners',]})
