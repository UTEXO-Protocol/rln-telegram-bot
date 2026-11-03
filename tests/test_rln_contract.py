"""Contracts for RLN PR #212 at revision 89ebe9f."""

import time
import unittest
from unittest.mock import Mock, patch

import requests
from embit import base58, bech32

# Bootstrap isolated settings before importing any bot modules.
# isort: off
from tests.support import fake_context, fake_update, settings as sett

# isort: on

from rgb_ln_telegram_bot import ln, msgs, tasks, telegram_bot
from rgb_ln_telegram_bot.database import (
    Purchase,
    PurchaseStatus,
    SendRequest,
    SendRequestStatus,
    init_db_session,
)
from rgb_ln_telegram_bot.exceptions import APIException, InvalidInvoice
from rgb_ln_telegram_bot.utils import (
    find_asset_label,
    parse_network,
    valid_bitcoin_address,
)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.http_patch = patch("rgb_ln_telegram_bot.ln.requests.request")
        self.http = self.http_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.http.return_value = Mock(ok=True, status_code=200)

    def test_complete_authenticated_invoice_is_preserved(self):
        invoice = (
            "rgb:invoice?endpoints=rpc://proxy&pubkey=abcdef&expiry=2000000000&encryption=ecies"
        )

        self.http.return_value.json.return_value = {"txid": "sent", "batch_transfer_idx": 4}
        with patch.object(sett, "RLN_AUTH_TOKEN", "test-biscuit"):
            self.assertEqual(ln.send_asset(invoice), "sent")
        self.http.assert_called_once_with(
            "POST",
            sett.LN_NODE_URL + "/sendrgbinvoice",
            timeout=sett.REQUESTS_TIMEOUT,
            headers={"Authorization": "Bearer test-biscuit"},
            json={
                "invoice": invoice,
                "asset_id": sett.ASSET_ID,
                "amount": sett.ASSET_AMOUNT_TO_SEND,
                "donation": True,
                "fee_rate": sett.FEE_RATE,
                "min_confirmations": 0,
            },
        )

    def test_test_settings_are_isolated(self):
        self.assertIn("rln-bot-test-", sett.DATA_DIR)
        self.assertEqual(sett.LN_NODE_URL, "http://127.0.0.1:9")
        self.assertEqual(sett.API_TOKEN, "YourAPIToken")

    def test_refresh_requires_filter(self):
        self.http.return_value.json.return_value = {}
        ln.refresh_transfers()
        self.assertEqual(self.http.call_args.kwargs["json"], {"filter": [], "skip_sync": False})

    def test_decode_errors_are_distinct_from_node_failures(self):
        for name, expected in (("InvalidInvoice", InvalidInvoice), ("LockedNode", APIException)):
            with self.subTest(name=name):
                self.http.return_value.json.return_value = {"name": name, "error": "details"}
                with self.assertRaises(expected) as caught:
                    ln.decode_rgb_invoice("input")
                self.assertIs(type(caught.exception), expected)

    def test_invalid_response_and_timeout(self):
        for body in ([], None, "invalid"):
            with self.subTest(body=body):
                self.http.return_value.json.return_value = body
                with self.assertRaises(APIException):
                    ln.decode_rgb_invoice("input")
        self.http.return_value.json.side_effect = ValueError("invalid JSON")
        with self.assertRaises(APIException):
            ln.decode_rgb_invoice("input")
        self.http.side_effect = requests.Timeout()
        with self.assertRaises(APIException):
            ln.decode_rgb_invoice("input")

    def test_ln_purchase_still_uses_auto_claim_invoice(self):
        self.http.return_value.json.return_value = {"invoice": "lnbcrt..."}
        self.assertEqual(ln.get_invoice(), "lnbcrt...")
        self.assertEqual(self.http.call_args.args[1], sett.LN_NODE_URL + "/lninvoice")
        self.assertEqual(
            self.http.call_args.kwargs["json"],
            {
                "amt_msat": sett.HTLC_MIN_MSAT,
                "expiry_sec": sett.INVOICE_EXPIRATION_SEC,
                "asset_id": sett.ASSET_ID,
                "asset_amount": sett.INVOICE_PRICE,
            },
        )


class AddressAndAssetTests(unittest.TestCase):
    def test_all_asset_buckets_including_bfa(self):
        for schema in ("nia", "uda", "ifa", "cfa", "bfa"):
            with self.subTest(schema=schema):
                self.assertEqual(
                    find_asset_label(
                        {schema: [{"asset_id": "asset", "ticker": "TOKEN", "name": "Token"}]},
                        "asset",
                    ),
                    "TOKEN",
                )
        self.assertEqual(
            find_asset_label({"bfa": [{"asset_id": "a", "name": "Bridged"}]}, "a"), "Bridged"
        )
        self.assertIsNone(find_asset_label({"bfa": None}, "missing"))

    def test_address_checksums_networks_and_witness_versions(self):
        for network, hrp, prefix in (
            ("Regtest", "bcrt", b"\x6f"),
            ("Mainnet", "bc", b"\x00"),
            ("Testnet", "tb", b"\x6f"),
            ("Testnet4", "tb", b"\x6f"),
            ("Signet", "tb", b"\x6f"),
            ("SignetCustom", "tb", b"\x6f"),
        ):
            with self.subTest(network=network):
                self.assertEqual(parse_network(network), network)
                legacy = base58.encode_check(prefix + bytes(range(20)))
                self.assertTrue(valid_bitcoin_address(legacy, network))
                for version, size in ((0, 20), (0, 32), (1, 32)):
                    address = bech32.encode(hrp, version, bytes(range(size)))
                    self.assertTrue(valid_bitcoin_address(address, network))
                    self.assertTrue(valid_bitcoin_address(address.upper(), network))
                    self.assertFalse(valid_bitcoin_address(address[:-1] + "!", network))
                    self.assertFalse(
                        valid_bitcoin_address(address, "Mainnet" if hrp != "bc" else "Regtest")
                    )
        for invalid in ("", "not an address", "bcrt1", "₿", "111111"):
            self.assertFalse(valid_bitcoin_address(invalid, "Regtest"))


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        sessions = init_db_session("sqlite:///:memory:")
        self.addCleanup(sessions.bind.dispose)
        self.addCleanup(sessions.remove)
        patcher = patch.object(sett, "Session", sessions)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.invoice = "rgb:complete-invoice-with-authentication"
        self.decoded = {
            "network": "Regtest",
            "recipient_type": "Blind",
            "asset_id": None,
            "assignment": {"type": "Any"},
            "expiration_timestamp": int(time.time()) + 3600,
        }
        self.update = fake_update(self.invoice)

    async def send_invoice(self, decoded=None):
        await telegram_bot.get_asset_handler(self.update, None)
        with (
            patch.object(telegram_bot, "decode_rgb_invoice", return_value=decoded or self.decoded),
            patch.object(telegram_bot, "send_asset", return_value="txid") as send,
            patch.object(telegram_bot, "refresh_transfers"),
        ):
            await telegram_bot.msg_handler(self.update, None)
            return send

    async def test_success_stores_complete_invoice_and_blocks_replay(self):
        send = await self.send_invoice()
        send.assert_called_once_with(self.invoice)
        with sett.Session() as session:
            request = session.query(SendRequest).one()
            self.assertEqual(request.status, SendRequestStatus.SUCCESS)
            self.assertEqual(request.rgb_invoice, self.invoice)
        send = await self.send_invoice()
        send.assert_not_called()
        self.assertEqual(
            self.update.message.reply_text.call_args.args[0], msgs.RGB_INVOICE_ALREADY_USED
        )

    async def test_invalid_invoice_constraints_never_send(self):
        for changes, message in (
            ({"network": "Signet"}, msgs.RGB_INVOICE_INVALID_NETWORK),
            ({"recipient_type": "Witness"}, msgs.RGB_INVOICE_INVALID_TYPE),
            ({"asset_id": "different"}, msgs.RGB_INVOICE_WRONG_ASSET),
            (
                {"assignment": {"type": "Fungible", "value": sett.ASSET_AMOUNT_TO_SEND + 1}},
                msgs.RGB_INVOICE_WRONG_AMOUNT(),
            ),
            ({"assignment": {"type": "NonFungible"}}, msgs.RGB_INVOICE_WRONG_AMOUNT()),
            ({"expiration_timestamp": int(time.time()) - 1}, msgs.RGB_INVOICE_EXPIRED),
        ):
            with self.subTest(changes=changes):
                send = await self.send_invoice(self.decoded | changes)
                send.assert_not_called()
                self.assertEqual(self.update.message.reply_text.call_args.args[0], message)

    async def test_explicit_and_unspecified_fungible_amounts(self):
        for amount in (0, sett.ASSET_AMOUNT_TO_SEND):
            with self.subTest(amount=amount):
                self.update.effective_user.id += 1
                self.update.message.text += str(amount)
                send = await self.send_invoice(
                    self.decoded | {"assignment": {"type": "Fungible", "value": amount}}
                )
                send.assert_called_once()

    async def test_node_decode_failure_is_not_reported_as_bad_invoice(self):
        with (
            patch.object(telegram_bot, "decode_rgb_invoice", side_effect=APIException("locked")),
            self.assertLogs(telegram_bot.LOGGER, level="ERROR"),
        ):
            self.assertEqual(
                await telegram_bot._validate_user_input(self.update, self.invoice, True, True),
                (None, None),
            )
        self.assertEqual(self.update.message.reply_text.call_args.args[0], msgs.RLN_REQUEST_FAILED)

    async def test_btc_address_with_both_requests_pending(self):
        address = bech32.encode("bcrt", 1, bytes(range(32)))
        with patch.object(telegram_bot, "decode_rgb_invoice", side_effect=InvalidInvoice()):
            self.assertEqual(
                await telegram_bot._validate_user_input(self.update, address, True, True),
                (None, address),
            )

    async def test_lightning_delivery_waits_for_succeeded(self):
        with sett.Session() as session:
            session.add(Purchase("lnbcrt...", 123))
            session.commit()
        context = fake_context()
        with patch.object(tasks, "get_invoice_status") as status:
            for value in ("Pending", "Claimable", "Claiming"):
                status.return_value = value
                await tasks.get_invoice_check_task(context)
                context.bot.send_sticker.assert_not_called()
            status.return_value = "Succeeded"
            await tasks.get_invoice_check_task(context)
            await tasks.get_invoice_check_task(context)
        context.bot.send_sticker.assert_awaited_once()
        with sett.Session() as session:
            self.assertEqual(session.query(Purchase).one().status, PurchaseStatus.DELIVERED)


if __name__ == "__main__":
    unittest.main()
