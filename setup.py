from setuptools import setup


with open("requirements.txt") as f:
    requirements = f.read().splitlines()
with open("README.md") as f:
    long_description = f.read()


setup(
    name='dastro_bot',
    version='1.0.3',
    description='Discord bot for Star Citizen players',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/Mirdalan/discord_astro_bot',
    author='Michal Chrzanowski',
    author_email='michrzan@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        'Topic :: Games/Entertainment',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='star citizen discord bot',
    install_requires=requirements,
    extras_require={
        ':sys_platform == "win32"': [
            'websocket-client==0.46.0'
        ],
        ':"linux" in sys_platform': [
            'websocket-client==0.44.0'
        ]
    },
    packages=['dastro_bot', 'dastro_bot._default_settings'],
    package_data={'': ['discord_bot.json', 'discord_bot.service']},
    include_package_data=True,
    python_requires='~=3.5',
)
