from setuptools import find_packages, setup

from pathlib import Path

DESCRIPTION = "This is a package to encapsulate lambda code"
PACKAGE_NAME = "python_package"
ROOT_DIR = Path(__file__).parent


# Packages that are required for this module to be executed
def list_reqs(fname="requirements.txt"):
    with open(fname) as fd:
        return fd.read().splitlines()


author = "Wesley"
setup(
    name=PACKAGE_NAME,
    version="0.0.1",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    author=author,
    maintainer=author,
    url="",
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    long_description_content_type="text/markdown",
    license="MIT",
    install_requires=list_reqs(),
    extras_require={},
)
