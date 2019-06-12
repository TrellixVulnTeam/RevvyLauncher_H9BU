#!/bin/python3
import json
import os
import shutil
import subprocess
import sys
import tarfile
import hashlib

from version import Version


def read_version(file):
    with open(file, 'r') as mf:
        manifest = json.load(mf)
    return Version(manifest['version'])


def file_hash(file):
    hash_fn = hashlib.md5()
    with open(file, "rb") as f:
        hash_fn.update(f.read())
    return hash_fn.hexdigest()


def subprocess_cmd(command):
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
        for line in iter(process.stdout.readline, b''):
            sys.stdout.write(line)
            if process.poll() is not None:
                break
        return process.returncode
    except BrokenPipeError:
        return 0


def main(directory):
    directory = os.path.abspath(directory)
    install_directory = os.path.join(directory, "installed")
    print('Started Revvy loader in {}'.format(directory))
    skip_frameworks = []

    while True:
        # try to install update and select version to run
        installed_versions = []

        newest = (Version("0.0"), "")
        has_newest = False

        # find newest framework
        for fw_dir in os.listdir(install_directory):
            fw_dir = os.path.join(install_directory, fw_dir)
            if fw_dir not in skip_frameworks:
                manifest_file = os.path.join(fw_dir, 'manifest.json')
                print(manifest_file)
                if os.path.isfile(manifest_file):
                    version = read_version(manifest_file)
                    installed_versions.append(version)
                    if newest[0] is None or newest[0] < version:
                        newest = (version, fw_dir)
                        print('Found version {}'.format(version))
                        has_newest = True

        # check for update file
        data_dir = os.path.join(directory, 'data', 'ble')
        print("Looking for update file in {}".format(data_dir))
        framework_update_file = os.path.join(data_dir, '2.data')
        framework_update_meta_file = os.path.join(data_dir, '2.meta')

        # if found - framework update process:
        if os.path.isfile(framework_update_file) and os.path.isfile(framework_update_meta_file):
            print("Found update file")
            update_file_valid = False
            with open(framework_update_meta_file, 'r') as fup_mf:
                metadata = json.load(fup_mf)
                if metadata['length'] == os.stat(framework_update_file).st_size:
                    if file_hash(framework_update_file) == metadata['md5']:
                        update_file_valid = True
                    else:
                        print('Update file hash mismatch')
                else:
                    print('Update file length mismatch')

            # if valid:
            if update_file_valid:
                print('Installing update')
                # extract to temp dir
                tmp_dir = os.path.join(install_directory, 'tmp')
                if os.path.isdir(tmp_dir):
                    print('Removing old: {}'.format(tmp_dir))
                    shutil.rmtree(tmp_dir)  # probably failed update?

                print('Extracting update package to: {}'.format(tmp_dir))
                with tarfile.open(framework_update_file, "r:gz") as tar:
                    tar.extractall(path=tmp_dir)

                # integrity check
                new_manifest_path = os.path.join(tmp_dir, 'manifest.json')
                with open(new_manifest_path, 'r') as mf:
                    new_manifest = json.load(mf)

                version_to_install = Version(new_manifest['version'])

                if version_to_install in installed_versions or version_to_install < newest[0]:
                    print('Skip installing {}'.format(version_to_install))
                    shutil.rmtree(tmp_dir)  # already installed or newer exists
                else:
                    print('Update version: {}'.format(version_to_install))
                    # rename temp dir to revvy-{version}
                    new_dir = os.path.join(install_directory, 'revvy-{}'.format(version_to_install))

                    print('Renaming {} to {}'.format(tmp_dir, new_dir))
                    shutil.move(tmp_dir, new_dir)

                    print('Running setup')
                    lines = [
                        # setup virtual env
                        'python3 -m venv {}/install/venv'.format(new_dir),
                        # activate venv
                        'sh {}/install/venv/bin/activate'.format(new_dir),
                        # install pip dependencies
                        'pip3 install -r {}/install/requirements.txt --no-index --find-links file:///{}/install/packages'.format(new_dir, new_dir)
                    ]
                    subprocess_cmd("\n".join(lines))

                    # select to be started
                    newest = (version_to_install, new_dir)
                    has_newest = True

                # remove update file
                os.unlink(framework_update_file)
                os.unlink(framework_update_meta_file)

        # TODO: make sure we don't have an inoperable robot
        if not has_newest:
            print('No frameworks installed!')
            return  # ?

        # start framework, wait for return value

        script_lives = True
        while script_lives:
            print('Starting {}'.format(newest[1]))
            lines = [
                # activate venv
                'sh {}/install/venv/bin/activate'.format(newest[1]),
                # start script
                'python3 -u {}/revvy.py'.format(newest[1])
            ]
            try:
                return_value = subprocess_cmd("\n".join(lines))
            except KeyboardInterrupt:
                return_value = 0

            print('Script exited with {}'.format(return_value))
            if return_value == 0:
                # manual exit
                return
            elif return_value == 1:
                # if script dies with error, restart [maybe measure runtime and if shorter than X and disable]
                pass
            elif return_value == 2:
                # if script dies with integrity error, restart process and skip framework
                skip_frameworks.append(newest[1])
                script_lives = False
            else:
                # if script exits with firmware update request, restart whole loop
                script_lives = False


if __name__ == "__main__":
    directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(directory)
    main('.')
