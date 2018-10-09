#!/usr/bin/env bash

python setup.py bdist_wheel
rm -rf ./dastro_bot.egg-info
rm -rf ./build
