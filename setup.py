from setuptools import setup

setup(
    name='spotify-dl',
    version='0.0.1',
    packages=['spotifyDL'],
    entry_points={
        'console_scripts': [
            'spotify-dl = spotifyDL.__main__:main'
        ]
    },
    install_requires=[
        'setuptools',
        'click',
        'pyfiglet',
        'requests',
        'bs4',
        'beautifulsoup4',
        'eyed3',
        'tqdm',
        'Pillow',
        'ytmusicapi',
        'youtube_dl',
        'simple-chalk~=0.1.0',
    ]
)
