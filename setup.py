import os

try:
    from setuptools import find_packages, setup
except AttributeError:
    from setuptools import find_packages, setup

NAME = 'OASYS1-ESRF-Extensions'
VERSION = '0.0.1'
ISRELEASED = True

DESCRIPTION = 'OASYS extension for the ESRF'
README_FILE = os.path.join(os.path.dirname(__file__), 'README.md')
LONG_DESCRIPTION = open(README_FILE).read()
AUTHOR = 'Luca Rebuffi, Manuel Sanchez del Rio'
AUTHOR_EMAIL = 'lrebuffi@anl.gov, srio@serf.eu'
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
)

PACKAGES = find_packages(exclude=('*.tests', '*.tests.*', 'tests.*', 'tests'))

PACKAGE_DATA = {
    "orangecontrib.esrf.wofry.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
    "orangecontrib.esrf.syned.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
    "orangecontrib.esrf.shadow.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
    "orangecontrib.esrf.srw.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
}

NAMESPACE_PACAKGES = ["orangecontrib",
                      "orangecontrib.esrf",
                      "orangecontrib.esrf.wofry",
                      "orangecontrib.esrf.syned",
                      "orangecontrib.esrf.shadow",
                      "orangecontrib.esrf.srw",
                      "orangecontrib.esrf.wofry.widgets",
                      "orangecontrib.esrf.syned.widgets",
                      "orangecontrib.esrf.shadow.widgets",
                      "orangecontrib.esrf.srw.widgets",
                      ]

ENTRY_POINTS = {
    'oasys.addons' : ("WOFRY ESRF Extension = orangecontrib.esrf.wofry",
                      "SYNED ESRF Extension = orangecontrib.esrf.syned",
                      "Shadow ESRF Extension = orangecontrib.esrf.shadow",
                      "SRW ESRF Extension = orangecontrib.esrf.srw",
                      ),
    'oasys.widgets' : (
        "WOFRY ESRF Extension = orangecontrib.esrf.wofry.widgets.extension",
        "SYNED ESRF Extension = orangecontrib.esrf.syned.widgets.extension",
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
