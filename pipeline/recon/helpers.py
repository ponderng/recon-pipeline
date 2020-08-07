import sys
import pickle
import typing
import inspect
import pkgutil
import importlib
import ipaddress
import json
import re
from pathlib import Path
from cmd2.ansi import style

from collections import defaultdict

from ..recon.config import defaults


def meets_requirements(requirements, exception):
    """ Determine if tools required to perform task are installed. """
    tools = get_tool_state()

    for tool in requirements:
        if not tools.get(tool).get("installed"):
            if exception:
                raise RuntimeError(
                    style(f"[!!] {tool} is not installed, and is required to run this scan", fg="bright_red")
                )
            else:
                return False

    return True


def get_tool_state() -> typing.Union[dict, None]:
    """ Load current tool state from disk. """
    tools = Path(defaults.get("tools-dir")) / ".tool-dict.pkl"

    if tools.exists():
        return pickle.loads(tools.read_bytes())


def get_scans():
    """ Iterates over the recon package and its modules to find all of the classes that end in [Ss]can.

    **A contract exists here that says any scans need to end with the word scan in order to be found by this function.**

    Example:
        ``defaultdict(<class 'list'>, {'AmassScan': ['pipeline.recon.amass'], 'MasscanScan': ['pipeline.recon.masscan'], ... })``

    Returns:
        dict containing mapping of ``classname -> [modulename, ...]`` for all potential recon-pipeline commands
    """
    scans = defaultdict(list)

    file = Path(__file__).expanduser().resolve()
    web = file.parent / "web"
    recon = file.parents[1] / "recon"

    lib_paths = [str(web), str(recon)]

    # recursively walk packages; import each module in each package
    # walk_packages yields ModuleInfo objects for all modules recursively on path
    # prefix is a string to output on the front of every module name on output.
    for loader, module_name, is_pkg in pkgutil.walk_packages(path=lib_paths, prefix=f"{__package__}."):
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            # skipping things like recon.aquatone, not entirely sure why they're showing up...
            pass

    # walk all modules, grabbing classes that we've written and add them to the classlist defaultdict
    # getmembers returns all members of an object in a list of tuples (name, value)
    for name, obj in inspect.getmembers(sys.modules[__package__]):
        if inspect.ismodule(obj) and not name.startswith("_"):
            # we're only interested in modules that don't begin with _ i.e. magic methods __len__ etc...

            for sub_name, sub_obj in inspect.getmembers(obj):
                # now we only care about classes that end in [Ss]can
                if inspect.isclass(sub_obj) and sub_name.lower().endswith("scan"):
                    # final check, this ensures that the tools necessary to AT LEAST run this scan are present
                    # does not consider upstream dependencies
                    try:
                        requirements = sub_obj.requirements
                        exception = False  # let meets_req know we want boolean result
                        if not meets_requirements(requirements, exception):
                            continue
                    except AttributeError:
                        # some scan's haven't implemented meets_requirements yet, silently allow them through
                        pass

                    scans[sub_name].append(f"{__package__}.{name}")

    return scans


def is_ip_address(ipaddr):
    """ Simple helper to determine if given string is an ip address or subnet """
    try:
        ipaddress.ip_interface(ipaddr)
        return True
    except ValueError:
        return False


def get_ip_address_version(ipaddr):
    """ Simple helper to determine whether a given ip address is ipv4 or ipv6 """
    if is_ip_address(ipaddr):
        if isinstance(ipaddress.ip_address(ipaddr), ipaddress.IPv4Address):  # ipv4 addr
            return "4"
        elif isinstance(ipaddress.ip_address(ipaddr), ipaddress.IPv6Address):  # ipv6
            return "6"


def is_inscope(hostname, scope_file):
    """ Check given hostname against scope file and return True if it is """
    # Use an default-allow rule,
    # so if there is no match in "include" or "exclude", it is within scope
    in_scope = True

    if scope_file == "":
        return in_scope

    # Load Scope file
    with open(scope_file, "r") as f:
        scope = json.load(f)

    # parse json data
    for block in scope['target']['scope']['exclude']:
        # Does URL match an excluded hostname?
        if re.search(block['host'], hostname):
            # If so, check for a more specific allow entry
            for allow in scope['target']['scope']['include']:
                # remove special chars in allow entry to make a domain name
                allow_n = allow['host'].replace('\\', '').replace('^', '').replace('$', '')
                # test the block entry against the normalized domain name
                if re.search(block['host'], allow_n):
                    # if the allowed domain name fits in the block domain entry
                    # , then it must be more specific.
                    # Test URL against the allow entry
                    if re.search(allow['host'], hostname):
                        # If it matches, mark as true
                        in_scope = True
                    else:
                        in_scope = False
                else:
                    in_scope = False
    return in_scope
