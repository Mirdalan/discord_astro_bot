#!/usr/bin/env bash

python setup.py sdist bdist_wheel

#twine upload --repository-url https://test.pypi.org/legacy/ dist/*

rm -rf ./dastro_bot.egg-info
rm -rf ./build
