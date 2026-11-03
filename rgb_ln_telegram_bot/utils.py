"""Utilities module."""

import os
import sys
from configparser import ConfigParser, MissingSectionHeaderError

from embit import base58, bech32
from embit.networks import NETWORKS

_ADDRESS_NETWORKS = {
    "Mainnet": "main",
    "Regtest": "regtest",
    "Signet": "signet",
    "Testnet": "test",
    "Testnet4": "test",
    "SignetCustom": "signet",
}


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
    """Validate and retain RLN's network name for invoice comparisons."""
    if network not in _ADDRESS_NETWORKS:
        die(f"Node is running on an unsupported network: {network}")
    return network


def valid_bitcoin_address(address, network):
    """Check Base58Check or SegWit/Bech32m checksums and network prefixes."""
    params = NETWORKS[_ADDRESS_NETWORKS[network]]
    try:
        payload = base58.decode_check(address)
        return len(payload) == 21 and payload[:1] in (params["p2pkh"], params["p2sh"])
    except ValueError:
        version, _program = bech32.decode(params["bech32"], address)
        return version is not None


def find_asset_label(assets, asset_id):
    """Return ticker or name for asset_id across all listassets schema buckets."""
    for bucket in ("nia", "uda", "ifa", "cfa", "bfa"):
        for asset in assets.get(bucket) or []:
            if asset.get("asset_id") == asset_id:
                return asset.get("ticker") or asset.get("name")
    return None
