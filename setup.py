import os

import stepic_pytest

from pip.req import parse_requirements
from setuptools import setup


README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

requirements_base = parse_requirements('requirements/base.txt')
install_requires = [str(req.req) for req in requirements_base]

setup(
    name='stepic-pytest',
    version=stepic_pytest.__version__,
    packages=['stepic_pytest'],
    install_requires=install_requires,
    author='Stepic Team',
    description="Test scenario runner for Stepic admin quiz",
    long_description=README,
    url='https://stepic.org',
    entry_points={'pytest11': ['stepic = stepic_pytest.plugin']},
)
