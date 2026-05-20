"""Utilities module."""

import os
import site
import sys
from configparser import ConfigParser, MissingSectionHeaderError


def _ensure_rgb_lib_dylib():
    """UTXO wheels ship librgblibuniffi.dylib; older bindings look for libuniffi.dylib."""
    for site_dir in site.getsitepackages():
        pkg_dir = os.path.join(site_dir, "rgb_lib")
        dylib = os.path.join(pkg_dir, "librgblibuniffi.dylib")
        link = os.path.join(pkg_dir, "libuniffi.dylib")
        if os.path.isfile(dylib) and not os.path.exists(link):
            os.symlink("librgblibuniffi.dylib", link)


_ensure_rgb_lib_dylib()

from rgb_lib import BitcoinNetwork


def die(message=None, exit_code=1):
    """Print message to stderr and exit with the requested error code."""
    if message:
        print(message, file=sys.stderr)
    sys.exit(exit_code)


def parse_config():
    """Parse the configuration file."""
    if not os.path.exists("config.ini"):
        die("config.ini not found, copy and eventually edit the config.ini.sample file")
    raw_config = ConfigParser()
    config_section = "config"
    try:
        raw_config.read("config.ini", encoding="utf-8")
        if not raw_config.has_section(config_section):
            raise RuntimeError
    except (MissingSectionHeaderError, RuntimeError):
        die(f"config.ini should contain a [{config_section}] section")
    return raw_config["config"]


def get_or_exit(conf, var_name, integer=False):
    """Get the requested config option, exit when missing."""
    config_val = conf.get(var_name)
    if config_val is None:
        die(f"No {var_name} in config")
    if integer:
        if not config_val.isdigit():
            die("the config variable {var_name} must be an integer")
        return int(config_val)
    return config_val


def get_or_default(conf, var_name, default_val):
    """Get the requested config option, use default when missing."""
    config_val = conf.get(var_name)
    return default_val if config_val is None else config_val


def parse_network(network):
    """Parse the given network string and return the corresponding enum."""
    match network:
        case "Mainnet":
            return BitcoinNetwork.MAINNET
        case "Regtest":
            return BitcoinNetwork.REGTEST
        case "Signet":
            return BitcoinNetwork.SIGNET
        case "Testnet":
            return BitcoinNetwork.TESTNET
        case "Testnet4":
            return BitcoinNetwork.TESTNET4
        case "SignetCustom":
            return BitcoinNetwork.SIGNET_CUSTOM
        case _:
            die(f"Node is running on an unsupported network: {network}")


def find_asset_label(assets, asset_id):
    """Return ticker or name for asset_id across all listassets schema buckets."""
    for bucket in ("nia", "uda", "ifa", "cfa"):
        for asset in assets.get(bucket) or []:
            if asset.get("asset_id") == asset_id:
                return asset.get("ticker") or asset.get("name")
    return None
