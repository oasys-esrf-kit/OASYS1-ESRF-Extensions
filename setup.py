# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2025 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/

import os

try:
    from setuptools import find_packages, setup
except AttributeError:
    from setuptools import find_packages, setup

NAME = 'OASYS1-ESRF-Extensions'
VERSION = '0.0.93'
ISRELEASED = True

DESCRIPTION = 'OASYS extension for the ESRF'
README_FILE = os.path.join(os.path.dirname(__file__), 'README.md')
LONG_DESCRIPTION = open(README_FILE).read()
AUTHOR = 'Manuel Sanchez del Rio, Juan Reyes-Herrera, Luca Rebuffi'
AUTHOR_EMAIL = 'srio@esrf.eu'
URL = 'https://github.com/oasys-esrf-kit/OASYS1-ESRF-Extensions'
DOWNLOAD_URL = 'https://github.com/oasys-esrf-kit/OASYS1-ESRF-Extensions'
LICENSE = 'GPLv3'

KEYWORDS = (
    'raytracing',
    'simulator',
    'oasys1',
)

CLASSIFIERS = (
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: Qt',
    'Environment :: Console',
    'Environment :: Plugins',
    'Programming Language :: Python :: 3',
    'Intended Audience :: Science/Research',
)

SETUP_REQUIRES = (
    'setuptools',
)

INSTALL_REQUIRES = (
    'setuptools',
    'oasys-barc4ro>=2024.11.13',
    'pandas',
    'numba',
    'shadow4>=0.1.49',
    'xoppylib>=1.0.30',
    'crystalpy>=0.0.24',
    'accelerator-toolbox==0.6.1',
)

PACKAGES = find_packages(exclude=('*.tests', '*.tests.*', 'tests.*', 'tests'))

PACKAGE_DATA = {
    "orangecontrib.esrf.oasys.widgets.extension":["icons/*.png", "icons/*.jpg"],
    "orangecontrib.esrf.wofry.widgets.extension":["icons/*.png", "icons/*.jpg"],
    "orangecontrib.esrf.xoppy.widgets.extension": ["icons/*.png", "icons/*.jpg"],
    "orangecontrib.esrf.syned.widgets.extension":["icons/*.png", "icons/*.jpg"],
    "orangecontrib.esrf.shadow.widgets.extension":["icons/*.png", "icons/*.jpg", "miscellanea/*.txt"],
    "orangecontrib.esrf.srw.widgets.extension":["icons/*.png", "icons/*.jpg"],
}

NAMESPACE_PACAKGES = ["orangecontrib",
                      "orangecontrib.esrf",
                      "orangecontrib.esrf.oasys",
                      "orangecontrib.esrf.wofry",
                      "orangecontrib.esrf.xoppy",
                      "orangecontrib.esrf.syned",
                      "orangecontrib.esrf.shadow",
                      "orangecontrib.esrf.srw",
                      "orangecontrib.esrf.oasys.widgets",
                      "orangecontrib.esrf.wofry.widgets",
                      "orangecontrib.esrf.xoppy.widgets",
                      "orangecontrib.esrf.syned.widgets",
                      "orangecontrib.esrf.shadow.widgets",
                      "orangecontrib.esrf.srw.widgets",
                      ]

ENTRY_POINTS = {
    'oasys.addons' : ("Oasys ESRF Extension = orangecontrib.esrf.oasys",
                      "Wofry ESRF Extension = orangecontrib.esrf.wofry",
                      "XOPPY ESRF Extension = orangecontrib.esrf.xoppy",
                      "Syned ESRF Extension = orangecontrib.esrf.syned",
                      "Shadow ESRF Extension = orangecontrib.esrf.shadow",
                      "SRW ESRF Extension = orangecontrib.esrf.srw",
                      ),
    'oasys.widgets' : (
        "Oasys ESRF Extension = orangecontrib.esrf.oasys.widgets.extension",
        "Wofry ESRF Extension = orangecontrib.esrf.wofry.widgets.extension",
        "XOPPY ESRF Extension = orangecontrib.esrf.xoppy.widgets.extension",
        "Syned ESRF Extension = orangecontrib.esrf.syned.widgets.extension",
        "Shadow ESRF Extension = orangecontrib.esrf.shadow.widgets.extension",
        "SRW ESRF Extension = orangecontrib.esrf.srw.widgets.extension",
    ),
    'oasys.menus' : ("esrfoasysmenu = orangecontrib.esrf.menu",)
}

if __name__ == '__main__':
    try:
        import PyMca5, PyQt4

        raise NotImplementedError("This version of ESRF Oasys Extensions doesn't work with Oasys1 beta.\nPlease install OASYS1 final release: http://www.elettra.eu/oasys.html")
    except:
        setup(
              name = NAME,
              version = VERSION,
              description = DESCRIPTION,
              long_description = LONG_DESCRIPTION,
              author = AUTHOR,
              author_email = AUTHOR_EMAIL,
              url = URL,
              download_url = DOWNLOAD_URL,
              license = LICENSE,
              keywords = KEYWORDS,
              classifiers = CLASSIFIERS,
              packages = PACKAGES,
              package_data = PACKAGE_DATA,
              #          py_modules = PY_MODULES,
              setup_requires = SETUP_REQUIRES,
              install_requires = INSTALL_REQUIRES,
              #extras_require = EXTRAS_REQUIRE,
              #dependency_links = DEPENDENCY_LINKS,
              entry_points = ENTRY_POINTS,
              namespace_packages=NAMESPACE_PACAKGES,
              include_package_data = True,
              zip_safe = False,
              )
