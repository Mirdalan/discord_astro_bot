import os
from shutil import copyfile

import sys


DEFAULT_FILES_DIR = "_default_settings"


def deploy_default_files(destination_dir="discord_bot"):
    module_dir = os.path.dirname(os.path.realpath(__file__))
    default_files_dir = os.path.join(module_dir, DEFAULT_FILES_DIR)
    for item in os.listdir(default_files_dir):
        source_file = os.path.join(default_files_dir, item)
        if os.path.isfile(source_file):
            copyfile(source_file, os.path.join(destination_dir, item))

def start_project(name="discord_bot"):
    destination_dir = os.path.join(os.getcwd(), name)
    os.mkdir(destination_dir)
    deploy_default_files(destination_dir)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        start_project(sys.argv[1])
    else:
        print("Usage: python -m dastro_bot.install <directory_name>")
