from setuptools import find_packages, setup


setup(
    name='antares_bot',
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot[job-queue]",
        "aiosqlite",
        "objgraph",
    ],
    entry_points={
        'console_scripts': [
            'antares_bot = antares_bot.__main__:main',
        ],
    },
    use_scm_version={
        "local_scheme": lambda x: "",
    },
    setup_requires=['setuptools_scm'],
)
