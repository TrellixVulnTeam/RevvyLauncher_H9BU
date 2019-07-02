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


def cleanup_invalid_installations(directory):
    for fw_dir in os.listdir(directory):
        fw_dir = os.path.join(directory, fw_dir)
        manifest_file = os.path.join(fw_dir, 'installed')
        if not os.path.isfile(manifest_file):
            shutil.rmtree(fw_dir)


def has_update_package(directory):
    print("Looking for update files in {}".format(directory))
    framework_update_file = os.path.join(directory, '2.data')
    framework_update_meta_file = os.path.join(directory, '2.meta')
    if os.path.isfile(framework_update_file) and os.path.isfile(framework_update_meta_file):
        print("Found update file, validating...")
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

        if not update_file_valid:
            os.unlink(framework_update_file)
            os.unlink(framework_update_meta_file)

        return update_file_valid
    else:
        return False


def dir_for_version(version):
    return 'revvy-{}'.format(version)


def install_update_package(data_directory, install_directory):
    framework_update_file = os.path.join(data_directory, '2.data')
    framework_update_meta_file = os.path.join(data_directory, '2.meta')
    tmp_dir = os.path.join(install_directory, 'tmp')

    if os.path.isdir(tmp_dir):
        print('Removing stuck tmp dir: {}'.format(tmp_dir))
        shutil.rmtree(tmp_dir)  # probably failed update?

    print('Extracting update package to: {}'.format(tmp_dir))
    with tarfile.open(framework_update_file, "r:gz") as tar:
        tar.extractall(path=tmp_dir)

    # integrity check done by installed package, now only get the version
    new_manifest_path = os.path.join(tmp_dir, 'manifest.json')

    print('Reading package version')
    with open(new_manifest_path, 'r') as mf:
        new_manifest = json.load(mf)
        version_to_install = Version(new_manifest['version'])

        target_dir = os.path.join(install_directory, dir_for_version(version_to_install))
        if os.path.isdir(target_dir):
            print('Update seems to already been installed, skipping')
            version_to_install = None

    if version_to_install:
        print('Installing version: {}'.format(version_to_install))

        print('Renaming {} to {}'.format(tmp_dir, target_dir))
        shutil.move(tmp_dir, target_dir)

        print('Running setup')
        lines = [
            # setup virtual env
            'python3 -m venv {}/install/venv'.format(target_dir),
            # activate venv
            'sh {}/install/venv/bin/activate'.format(target_dir),
            # install pip dependencies
            'pip3 install -r {0}/requirements.txt --no-index --find-links file:///{0}/packages'.format(
                os.path.join(target_dir, 'install')),
            # create file that signals finished installation
            'touch {}/installed'.format(target_dir)
        ]
        subprocess_cmd("\n".join(lines))

        print('Removing update package')
        os.unlink(framework_update_file)
        os.unlink(framework_update_meta_file)
    else:
        # we don't want to install this package, remove sources
        shutil.rmtree(tmp_dir)
        os.unlink(framework_update_file)
        os.unlink(framework_update_meta_file)


def select_newest_package(directory, skipped_versions):
    newest = Version("0.0")
    newest_path = None

    # find newest framework
    for fw_dir in os.listdir(directory):
        fw_dir = os.path.join(directory, fw_dir)
        if fw_dir not in skipped_versions:
            manifest_file = os.path.join(fw_dir, 'manifest.json')
            if os.path.isfile(manifest_file):
                version = read_version(manifest_file)
                if newest is None or newest < version:
                    newest = version
                    print('Found version {}'.format(version))
                    newest_path = os.path.join(directory, dir_for_version(version))

    return newest_path


def start_framework(path):
    script_lives = True
    return_value = 0
    while script_lives:
        print('Starting {}'.format(path))
        lines = [
            # activate venv
            'sh {}/install/venv/bin/activate'.format(path),
            # start script
            'python3 -u {}/revvy.py'.format(path)
        ]
        try:
            return_value = subprocess_cmd("\n".join(lines))
        except KeyboardInterrupt:
            return_value = 0

        print('Script exited with {}'.format(return_value))
        if return_value == 1:
            # if script dies with error, restart [maybe measure runtime and if shorter than X and disable]
            pass
        else:
            script_lives = False

    return return_value


def startup(directory):
    skipped_versions = []

    install_directory = os.path.join(directory, "installed")
    data_directory = os.path.join(directory, 'data', 'ble')

    cleanup_invalid_installations(install_directory)
    if has_update_package(data_directory):
        install_update_package(data_directory, install_directory)

    path = select_newest_package(install_directory, skipped_versions)
    if path:
        return_value = start_framework(path)
        if return_value == 2:
            # if script dies with integrity error, restart process and skip framework
            skipped_versions.append(path)


def main(directory):
    startup(directory)
    # TODO: if script reaches this point, enter recovery mode


if __name__ == "__main__":
    directory = os.path.dirname(__file__)
    directory = os.path.abspath(directory)
    os.chdir(directory)
    main(directory)
