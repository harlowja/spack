# Copyright 2013-2020 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import llnl.util.tty as tty
from llnl.util.tty.colify import colify

import spack.cmd
import spack.cmd.common.arguments as arguments
import spack.environment as ev
import spack.repo
import spack.store

description = "show packages that depend on another"
section = "basic"
level = "long"


def setup_parser(subparser):
    subparser.add_argument(
        '-i', '--installed', action='store_true', default=False,
        help="List installed dependents of an installed spec, "
        "instead of possible dependents of a package.")
    subparser.add_argument(
        '-t', '--transitive', action='store_true', default=False,
        help="Show all transitive dependents.")
    arguments.add_common_arguments(subparser, ['spec'])


def inverted_dependencies():
    """Iterate through all packages and return a dictionary mapping package
       names to possible dependencies.

       Virtual packages are included as sources, so that you can query
       dependents of, e.g., `mpi`, but virtuals are not included as
       actual dependents.
    """
    dag = {}
    for pkg in spack.repo.path.all_packages():
        dag.setdefault(pkg.name, set())
        for dep in pkg.dependencies:
            deps = [dep]

            # expand virtuals if necessary
            if spack.repo.path.is_virtual(dep):
                deps += [s.name for s in spack.repo.path.providers_for(dep)]

            for d in deps:
                dag.setdefault(d, set()).add(pkg.name)
    return dag


def get_dependents(pkg_name, ideps, transitive=False, dependents=None):
    """Get all dependents for a package.

    Args:
        pkg_name (str): name of the package whose dependents should be returned
        ideps (dict): dictionary of dependents, from inverted_dependencies()
        transitive (bool, optional): return transitive dependents when True
    """
    if dependents is None:
        dependents = set()

    if pkg_name in dependents:
        return set()
    dependents.add(pkg_name)

    direct = ideps[pkg_name]
    if transitive:
        for dep_name in direct:
            get_dependents(dep_name, ideps, transitive, dependents)
    dependents.update(direct)
    return dependents


def dependents(parser, args):
    specs = spack.cmd.parse_specs(args.spec)
    if len(specs) != 1:
        tty.die("spack dependents takes only one spec.")

    if args.installed:
        env = ev.get_env(args, 'dependents')
        spec = spack.cmd.disambiguate_spec(specs[0], env)

        format_string = '{name}{@version}{%compiler}{/hash:7}'
        tty.msg("Dependents of %s" % spec.cformat(format_string))
        deps = spack.store.db.installed_relatives(
            spec, 'parents', args.transitive)
        if deps:
            spack.cmd.display_specs(deps, long=True)
        else:
            print("No dependents")

    else:
        spec = specs[0]
        ideps = inverted_dependencies()

        dependents = get_dependents(spec.name, ideps, args.transitive)
        dependents.remove(spec.name)
        if dependents:
            colify(sorted(dependents))
        else:
            print("No dependents")
