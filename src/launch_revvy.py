#!/bin/python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import hashlib
import time
import traceback
from json import JSONDecodeError
from version import Version


default_package_dir = 'default/packages'
installed_packages_dir = 'user/packages'
start_directories = [installed_packages_dir, default_package_dir]


def read_version(file):
    """Reads version from json formatted manifest file.

    Args:
        file: Path to a json formatted manifest file.

    Returns:
        A Version object containing the version json field of the provided file
        or None on error.
    """
    try:
        with open(file, 'r') as mf:
            manifest = json.load(mf)
        return Version(manifest['version'])
    except FileNotFoundError:
        print('File not found: {}'.format(file))
    except JSONDecodeError:
        print('Invalid json file: {}'.format(file))
    except KeyError:
        print('Json file is valid but there is no version in it: {}'.format(file))

    return None


def file_hash(file):
    """Calculates the md5 hash for the file provided.

    Args:
        file: Path to the file.

    Returns:
        The md5 hash string of the file or None on error.
        E.g.: 'd41d8cd98f00b204e9800998ecf8427e'

    Raises:
        IOError: An error occurred during opening/reading the file.
    """
    try:
        hash_fn = hashlib.md5()
        with open(file, "rb") as f:
            hash_fn.update(f.read())
        return hash_fn.hexdigest()
    except IOError:
        print('Could not calculate hash for {}'.format(file))
        print(traceback.format_exc())
        return None


def subprocess_cmd(command):
    """Executes shell commands

    Args:
        command: Newline separated commands to be executed in the shell

    Returns:
        Return code of execution
    """
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
    """Removes incomplete versions of fw installations.

    The presence of the 'installed' file proves that the installation
    completed successfully. For any fw directory without this sentinel,
    we remove the directory.

    Args:
        directory: Base directory, containing installations.
    """
    print("Cleaning up invalid installations")
    try:
        for fw_dir in os.listdir(directory):
            print("Checking {}".format(fw_dir))
            fw_dir = os.path.join(directory, fw_dir)
            if os.path.isdir(fw_dir):
                manifest_file = os.path.join(fw_dir, 'installed')
                if not os.path.isfile(manifest_file):
                    print('Removing {}'.format(fw_dir))
                    shutil.rmtree(fw_dir)
    except FileNotFoundError:
        print('No user packages exist')


def has_update_package(directory):
    """Checks if a valid fw update package is available.

    The '2.meta' json file contains length and md5 information about the update
    package named '2.data'. The code checks if these values are matching.

    Args:
        directory: (String) Directory path containing update package.

    Returns:
        True if update package is present and valid.
    """
    print("Looking for update files in {}".format(directory))
    framework_update_file = os.path.join(directory, '2.data')
    framework_update_meta_file = os.path.join(directory, '2.meta')
    update_file_valid = False

    if os.path.isfile(framework_update_file) and os.path.isfile(framework_update_meta_file):
        print("Found update file, validating...")
        try:
            with open(framework_update_meta_file, 'r') as fup_mf:
                metadata = json.load(fup_mf)
                if metadata['length'] == os.stat(framework_update_file).st_size:
                    if metadata['md5'] is not None and file_hash(framework_update_file) == metadata['md5']:
                        update_file_valid = True
                    else:
                        print('Update file hash mismatch')
                else:
                    print('Update file length mismatch')
        except IOError:
            print("Failed to read metadata")
        except (JSONDecodeError, KeyError):
            print("Update metadata corrupted, skipping update")

        if not update_file_valid:
            os.unlink(framework_update_file)
            os.unlink(framework_update_meta_file)

    return update_file_valid


def dir_for_version(version):
    """Generates directory name for a framework version.

    Args:
        version: A Version object.

    Returns:
        Directory name as a string.
    """
    return 'revvy-{}'.format(version)


def install_update_package(data_directory, install_directory):
    """Install update package.

    Extracts, validates and installs the update package. If any step of this
    process fails tries to clean up, and remove the corrupt update package.
    Installation creates a virtualenv, installs required packages via pip from
    a local repository, and places the 'installed' placeholder into the
    directory, as the final step, to prove that installation finished
    successfully.

    Args:
        data_directory: Directory path containing the fw update.
        install_directory: Directory path with the fw installations.
    """
    framework_update_file = os.path.join(data_directory, '2.data')
    framework_update_meta_file = os.path.join(data_directory, '2.meta')
    tmp_dir = os.path.join(install_directory, 'tmp')

    if os.path.isdir(tmp_dir):
        print('Removing stuck tmp dir: {}'.format(tmp_dir))
        shutil.rmtree(tmp_dir)  # probably failed update?

    # try to extract package
    try:
        print('Extracting update package to: {}'.format(tmp_dir))
        with tarfile.open(framework_update_file, "r:gz") as tar:
            tar.extractall(path=tmp_dir)
    except (ValueError, tarfile.TarError):
        print('Failed to extract package')
        os.unlink(framework_update_file)
        os.unlink(framework_update_meta_file)
        return

    # try to read package version
    # integrity check done by installed package, now only get the version
    version_to_install = read_version(os.path.join(tmp_dir, 'manifest.json'))

    print('Reading package version')
    if version_to_install is None:
        print('Failed to read package version')
        shutil.rmtree(tmp_dir)
        os.unlink(framework_update_file)
        os.unlink(framework_update_meta_file)
        return

    target_dir = os.path.join(install_directory, dir_for_version(version_to_install))
    if os.path.isdir(target_dir):
        print('Update seems to already been installed, skipping')
        # we don't want to install this package, remove sources
        shutil.rmtree(tmp_dir)
        os.unlink(framework_update_file)
        os.unlink(framework_update_meta_file)
        return

    print('Installing version: {}'.format(version_to_install))
    print('Renaming {} to {}'.format(tmp_dir, target_dir))
    shutil.move(tmp_dir, target_dir)

    print('Running setup')
    lines = [
        # setup virtual env
        'echo "Setting up venv"',
        'python3 -m venv {}/install/venv'.format(target_dir),
        # activate venv
        'echo "Activating venv"',
        'sh {}/install/venv/bin/activate'.format(target_dir),
        # install pip dependencies
        'echo "Installing dependencies"',
        'python3 -m pip install --no-cache-dir -r {0}/requirements.txt --no-index --find-links file:///{0}/packages'
        .format(os.path.join(target_dir, 'install')),
        # create file that signals finished installation
        'touch {}/installed'.format(target_dir)
    ]
    subprocess_cmd("\n".join(lines))

    print('Removing update package')
    os.unlink(framework_update_file)
    os.unlink(framework_update_meta_file)


def select_newest_package(directory, skipped_versions):
    """Finds latest, non blacklisted framework version.

    Checks all subdirectories in directory, reads the version information from
    the manifest.json files.

    Args:
        directory: Base directory of installed frameworks.
        skipped_versions: List of path names of framework versions to be
            skipped.

    Returns:
        String path for the newest version.
    """
    newest = Version("0.0")
    newest_path = None

    # find newest framework
    try:
        for fw_dir in os.listdir(directory):
            fw_dir = os.path.join(directory, fw_dir)
            if fw_dir not in skipped_versions:
                manifest_file = os.path.join(fw_dir, 'manifest.json')
                if os.path.isfile(manifest_file):
                    version = read_version(manifest_file)
                    if version is not None and (newest is None or newest < version):
                        newest = version
                        print('Found version {}'.format(version))
                        newest_path = os.path.join(directory, dir_for_version(version))
    except FileNotFoundError:
        print('Failed to select newest package')
        print(traceback.format_exc())

    return newest_path


def start_framework(path):
    """Runs revvy framework in its virtualenv.

    Args:
        path: (String) Path to directory containing the revvy code.

    Returns:
        Integer error code.
        See revvy/utils.py's RevvyStatusCode for actual codes.
        0 - OK
        other - ERROR, INTEGRITY_ERROR, UPDATE_REQUEST, etc...
    """
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
    """Runs revvy from directory.

    Handles the command line arguments of the script.
    Currently the only one is --install-only, which terminates execution after
    install.

    Steps:
    - Cleanup failed installations
    - Search for fw update and install it
    - Execute latest version
    - If execution terminates normally, finish
    - If execution terminates with integrity_error, exclude version and retry
    - Otherwise restart the same version

    Args:
        directory: Base directory containing installed version of the revvy
            framework.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-only', help='Install updates but do not start framework', action='store_true')
    parser.add_argument('--install-default', help='Install the default package. Requires --install-only'
                                                  ' and the filesystem must be writeable.', action='store_true')

    args = parser.parse_args()

    skipped_versions = []

    if args.install_only and args.install_default:
        install_directory = os.path.join(directory, default_package_dir)
    else:
        install_directory = os.path.join(directory, installed_packages_dir)

    data_directory = os.path.join(directory, 'user', 'ble')

    print('Install directory: {}'.format(install_directory))
    print('Data directory: {}'.format(data_directory))

    stop = False
    while not stop:
        cleanup_invalid_installations(install_directory)
        if has_update_package(data_directory):
            install_update_package(data_directory, install_directory)

        if args.install_only:
            print('--install-only flag is set, exiting')
            stop = True
        else:
            # configure AMP_EN to input
            subprocess_cmd("gpio -g mode 22 in")

            # read AMP_EN to detect if Revvy is ON
            amp_en = subprocess.check_output(["gpio", "read", "3"])
            while amp_en != b'1\n':
                print("Device is off... waiting")
                time.sleep(1)
                amp_en = subprocess.check_output(["gpio", "read", "3"])

            print("Device is on, start framework")
            # delay to wait hciuart device
            time.sleep(1)
            # try to look for a working update package
            path = select_newest_package(install_directory, skipped_versions)
            if not path:
                # if there is no such package, start the built in one
                path = select_newest_package(default_package_dir, [])

            if path:
                return_value = start_framework(path)
                if return_value == 0:
                    print('Manual exit')
                    stop = True
                elif return_value == 2:
                    # if script dies with integrity error, restart process and skip framework
                    print('Integrity error - add {} to skipped list'.format(path))
                    skipped_versions.append(path)
            else:
                # if, for some reason there is no built-in package, stop
                print('There are no more packages to try - exit')
                stop = True


def main(directory):
    startup(directory)
    # TODO: if script reaches this point, enter recovery mode


if __name__ == "__main__":
    current_directory = os.path.dirname(__file__)
    current_directory = os.path.abspath(current_directory)
    os.chdir(current_directory)
    main(current_directory)
