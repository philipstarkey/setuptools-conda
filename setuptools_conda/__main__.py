from pathlib import Path
from subprocess import call
import sys
import argparse

get_pyproject_toml_entry = None
get_setup_cfg_entry = None


def run(cmd, **kwargs):
    print('[running]:', ' '.join(cmd))
    rc = call(cmd, **kwargs)
    if rc:
        sys.exit(rc)
    return rc


def get_requires(proj):
    requires = get_pyproject_toml_entry(proj, 'build-system', 'requires')
    if requires is not None:
        print("Using build requirements from [build-system]/requires")
        return requires
    requires = get_setup_cfg_entry(proj, "dist_conda", "setup_requires")
    if requires is not None:
        print("Using build requirements from [dist_conda]/setup_requires")
        return requires
    requires = get_setup_cfg_entry(proj, "options", "setup_requires")
    if requires is not None:
        print("Using build requirements from [options]/setup_requires")
        return requires
    print("No build requirements found")
    requires = []


def get_channels(proj):
    channels = get_pyproject_toml_entry(proj, "tools", "setuptools-conda", "channels")
    if channels is not None:
        print("Using extra channels from [tools.setuptools-conda]/channels")
        return channels
    channels = get_setup_cfg_entry(proj, "dist_conda", "channels")
    if channels is not None:
        print("Using extra channels from [tools.setuptools-conda]/channels")
        return channels
    print("No extra channels specified")
    return []        


def main():
    # Since setuptools_conda is self-hosting, it needs toml and distlib to read its own
    # requirements just to know that it needs to install toml and distlib! So bootstrap
    # that up if necessary.

    parser = argparse.ArgumentParser(
        description="""Install the build requirements of a project with conda, and then
        run 'python setup.py', passing remaining arguments. This is similar to 'pip
        wheel' etc in the presence of a pyproject.toml file (but without build isolation
        - the dependencies will be installed in the current environment). A typical way
        to call this script would be as 'setuptools-conda . dist_conda [args]' from the
        working directory of a project, where '[args]' are any additional arguments you
        want to pass to the 'dist_conda' command. See 'python setup.py dist_conda -h'
        for a full list of arguments accepted by the 'dist_conda' command.

        Build requirements are searched for in the places in order, stopping on the
        first found:

        1. `[build-system]/requires in the project's pyproject.toml

        2. [dist_conda]/setup_requires in the project's setup.cfg

        3. [options]/setup_requires in the project's setup.cfg

        Additional conda channels to enable to install the build requirements are
        searched for in the following places in order, stopping on the first found:

        1. [tools.setuptools-conda]/channels in the project's pyproject.toml

        2. [dist_conda]/channels in the project's setup.cfg

        Note that when running 'python setup.py dist_conda', dist_conda will receive
        configuration from setup.cfg with higher priority, which is the opposite of what
        we do here. So use one or the other for configuring build dependencies, not both
        lest the two become inconsistent.
        """
    )

    parser.add_argument(
        'project',
        action="store",
        help="""Path to project; e.g. '.' if the project's `setup.py` and any of
        `pyproject.toml` or `setup.cfg` are in the current working directory.""",
    )

    parser.add_argument(
        action="store",
        dest="setup_args",
        nargs=argparse.REMAINDER,
        default=[],
        help="""Arguments to pass to setup.py as 'python setup.py [setup_args]'; e.g.
        'dist_conda --noarch'""",
    )

    args = parser.parse_args()

    # Bootstrap up our own requirements just to run the functions for getting
    # requirements:
    try:
        import toml
    except ImportError:
        run(['conda', 'install', '-y', 'toml'])
    try:
        import distlib
    except ImportError:
        run(['conda', 'install', '-y',  'distlib'])

    global get_pyproject_toml_entry
    global get_setup_cfg_entry

    from setuptools_conda.setuptools_conda import (
        get_pyproject_toml_entry,
        get_setup_cfg_entry,
        evaluate_requirements,
    )

    proj = Path(args.project)
    
    requires = get_requires(proj)
    requires = evaluate_requirements(requires)
    channels = get_channels(proj)

    chan_args = []
    for chan in channels:
        chan_args += ['--channel', chan]

    if requires:
        run(['conda', 'install', '-y',] + chan_args + requires)

    sys.exit(run([sys.executable, 'setup.py'] + args.setup_args, cwd=str(proj),))


if __name__ == '__main__':
    main()