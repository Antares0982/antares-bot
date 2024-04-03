from setuptools import find_packages, setup


setup(
    name='antares_bot',
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot[job-queue]",
        "aiosqlite",
        "objgraph",
    ],
    use_scm_version={
        "local_scheme": lambda x: "",
    },
    setup_requires=['setuptools_scm'],
)
