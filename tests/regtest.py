"""Exercise bot handlers on funded regtest nodes; no Telegram token or network calls."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path

import requests

# Bootstrap isolated settings before importing any bot modules.
# isort: off
from tests.support import fake_context, fake_update, settings as sett

# isort: on

from rgb_ln_telegram_bot import ln, tasks, telegram_bot
from rgb_ln_telegram_bot.database import (
    Purchase,
    PurchaseStatus,
    SendBtcRequest,
    SendBtcRequestStatus,
    SendRequest,
    SendRequestStatus,
)
from rgb_ln_telegram_bot.utils import find_asset_label


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def api(url, path, payload=None):
    response = requests.request(
        "GET" if payload is None else "POST", url + path, json=payload, timeout=60
    )
    response.raise_for_status()
    body = response.json()
    require("error" not in body, f"{path}: {body}")
    return body


async def run(args):
    require("rln-bot-test-" in sett.DATA_DIR, "Refusing to use a non-test bot database")
    # Both nodes and Bitcoin Core must explicitly report regtest before any mutation.
    for url in (args.bot_node, args.peer_node):
        require(api(url, "/networkinfo")["network"] == "Regtest", "Only regtest nodes are allowed")

    def btc(method, *params):
        response = requests.post(
            args.bitcoin_rpc,
            auth=(args.bitcoin_user, args.bitcoin_password),
            json={"jsonrpc": "1.0", "id": "bot-test", "method": method, "params": params},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        require(not body.get("error"), f"Bitcoin RPC failed: {body.get('error')}")
        return body["result"]

    require(btc("getblockchaininfo")["chain"] == "regtest", "Bitcoin Core must be regtest")
    mine_address = btc("getnewaddress")
    sett.LN_NODE_URL = args.bot_node
    sett.ASSET_ID = args.asset_id
    sett.ASSET_AMOUNT_TO_SEND = 42
    sett.SAT_AMOUNT_TO_SEND = 50000
    sett.INVOICE_PRICE = 1
    sett.ASSET_TICKER = find_asset_label(ln.list_assets(), args.asset_id)
    require(sett.ASSET_TICKER, "Bot node must already know the configured asset")
    ln.get_node_info()
    peer_assets = api(args.peer_node, "/listassets", {"filter_asset_schemas": []})
    require(
        find_asset_label(peer_assets, args.asset_id), "Peer must already know the configured asset"
    )
    asset_filter = {"asset_filter": {"type": "Id", "value": args.asset_id}}
    report = {
        "supported_rln_revision": Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("rln-revision")
        .read_text()
        .strip(),
        "bot_node": args.bot_node,
        "peer_node": args.peer_node,
        "asset_id": args.asset_id,
    }

    def balance(url):
        return api(url, "/assetbalance", {"asset_id": args.asset_id})

    async def wait_for(label, predicate, mine=False):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if mine:
                btc("generatetoaddress", 1, mine_address)
                for url in (args.bot_node, args.peer_node):
                    api(url, "/refreshtransfers", {"filter": [], "skip_sync": False})
            if predicate():
                return
            await asyncio.sleep(2)
        raise RuntimeError(f"Timed out: {label}")

    update = fake_update()
    context = fake_context()
    before = {"bot": balance(args.bot_node), "peer": balance(args.peer_node)}
    print("RGB faucet: create authenticated invoice, run /getasset and submit invoice", flush=True)
    # Keep maintenance endpoints covered, using the same bot task as production.
    await tasks.node_checks(context)
    received = api(
        args.peer_node,
        "/rgbinvoice",
        {
            "asset_id": args.asset_id,
            "assignment": {"type": "Fungible", "value": sett.ASSET_AMOUNT_TO_SEND},
            "expiration_timestamp": int(time.time()) + 3600,
            "min_confirmations": 1,
            "witness": False,
            "transport_endpoints": [args.proxy_endpoint],
        },
    )
    invoice = received["invoice"]
    decoded = ln.decode_rgb_invoice(invoice)
    require(decoded.get("public_key"), "Expected a protocol-1 invoice with a public key")
    await telegram_bot.get_asset_handler(update, context)
    update.message.text = invoice
    await telegram_bot.msg_handler(update, context)
    with sett.Session() as session:
        request = session.query(SendRequest).one()
        require(request.status == SendRequestStatus.SUCCESS, "RGB faucet request failed")
        require(request.rgb_invoice == invoice, "Original invoice was not persisted")
        rgb_txid = request.txid

    def settled():
        for url in (args.bot_node, args.peer_node):
            transfers = api(url, "/listtransfers", asset_filter | {"txid": rgb_txid})["transfers"]
            if not transfers or any(t["status"] != "Settled" for t in transfers):
                return False
        return (
            balance(args.peer_node)["spendable"]
            == before["peer"]["spendable"] + sett.ASSET_AMOUNT_TO_SEND
        )

    await wait_for("RGB settlement on both nodes", settled, mine=True)
    require(
        balance(args.bot_node)["spendable"]
        == before["bot"]["spendable"] - sett.ASSET_AMOUNT_TO_SEND,
        "Unexpected sender RGB balance",
    )
    report["rgb"] = {"txid": rgb_txid, "amount": sett.ASSET_AMOUNT_TO_SEND, "status": "Settled"}

    print("BTC faucet: run /getbtc, submit peer address, confirm the output", flush=True)
    address = api(args.peer_node, "/address", {})["address"]
    await telegram_bot.get_btc_handler(update, context)
    update.message.text = address
    await telegram_bot.msg_handler(update, context)
    with sett.Session() as session:
        request = session.query(SendBtcRequest).one()
        require(request.status == SendBtcRequestStatus.SUCCESS, "BTC faucet request failed")
        btc_txid = request.txid
    transaction = btc("getrawtransaction", btc_txid, True)
    require(
        any(
            o["scriptPubKey"].get("address") == address
            and round(o["value"] * 100000000) == sett.SAT_AMOUNT_TO_SEND
            for o in transaction["vout"]
        ),
        "BTC transaction did not pay the requested address and amount",
    )
    blocks = btc("generatetoaddress", 2, mine_address)
    confirmed = any(btc_txid in btc("getblock", block)["tx"] for block in blocks)
    require(confirmed, "BTC faucet transaction was not mined")
    report["btc"] = {"txid": btc_txid, "amount_sat": sett.SAT_AMOUNT_TO_SEND, "confirmed": True}

    print("LN purchase: run /getinvoice, pay from peer, wait for delivery", flush=True)
    before = {"bot": balance(args.bot_node), "peer": balance(args.peer_node)}
    await telegram_bot.get_invoice_handler(update, context)
    with sett.Session() as session:
        invoice = session.query(Purchase).one().invoice
    payment = api(
        args.peer_node,
        "/sendpayment",
        {"invoice": invoice, "asset_id": args.asset_id, "asset_amount": sett.INVOICE_PRICE},
    )
    require(payment.get("status") != "Failed", f"LN send failed: {payment}")
    await wait_for("LN invoice succeeded", lambda: ln.get_invoice_status(invoice) == "Succeeded")
    records = api(args.peer_node, "/listpayments")["payments"]
    paid = next(p for p in records if p["payment_hash"] == payment["payment_hash"])
    require(paid["status"] == "Succeeded", "Payer did not settle")
    require(
        hashlib.sha256(bytes.fromhex(paid["preimage"])).hexdigest() == paid["payment_hash"],
        "Invalid payment preimage",
    )
    await tasks.get_invoice_check_task(context)
    await tasks.get_invoice_check_task(context)
    with sett.Session() as session:
        require(
            session.query(Purchase).one().status == PurchaseStatus.DELIVERED,
            "Purchase not delivered",
        )
    context.bot.send_sticker.assert_awaited_once()
    require(
        balance(args.bot_node)["offchain_outbound"]
        == before["bot"]["offchain_outbound"] + sett.INVOICE_PRICE,
        "Wrong receiver LN asset delta",
    )
    require(
        balance(args.peer_node)["offchain_outbound"]
        == before["peer"]["offchain_outbound"] - sett.INVOICE_PRICE,
        "Wrong payer LN asset delta",
    )
    report["lightning"] = {
        "payment_hash": paid["payment_hash"],
        "status": "Succeeded",
        "purchase": "DELIVERED",
        "preimage_verified": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bot-node", required=True)
    parser.add_argument("--peer-node", required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--bitcoin-rpc", default="http://127.0.0.1:18443/wallet/miner")
    parser.add_argument("--bitcoin-user", default=os.environ.get("REGTEST_RPC_USER", "user"))
    parser.add_argument(
        "--bitcoin-password", default=os.environ.get("REGTEST_RPC_PASSWORD", "password")
    )
    parser.add_argument("--proxy-endpoint", default="rpc://127.0.0.1:3000/json-rpc")
    parser.add_argument("--output", type=Path, default=Path("logs/regtest.json"))
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
