import asyncio
import struct
import unittest

from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    PayloadType,
    WireError,
    decode_varint,
    encode_varint,
    frame,
    read_cast_message,
)


class WireTests(unittest.TestCase):
    def test_varint_round_trip(self):
        for value in (0, 1, 127, 128, 300, 2**32, 2**63 - 1):
            encoded = encode_varint(value)
            self.assertEqual((value, len(encoded)), decode_varint(encoded))

    def test_string_message_round_trip(self):
        message = CastMessage(
            source_id="sender-0",
            destination_id="receiver-0",
            namespace="urn:x-cast:test",
            payload_utf8='{"type":"PING"}',
        )
        self.assertEqual(message, CastMessage.decode(message.encode()))

    def test_binary_message_round_trip(self):
        message = CastMessage(
            source_id="sender-0",
            destination_id="receiver-0",
            namespace="urn:x-cast:binary",
            payload_type=PayloadType.BINARY,
            payload_binary=b"\x00\xffchallenge",
        )
        self.assertEqual(message, CastMessage.decode(message.encode()))

    def test_frame_has_network_order_length(self):
        message = CastMessage("a", "b", "c", payload_utf8="d")
        packet = frame(message)
        self.assertEqual(len(packet) - 4, struct.unpack(">I", packet[:4])[0])

    def test_reader_rejects_oversized_frame(self):
        async def check():
            reader = asyncio.StreamReader()
            reader.feed_data(struct.pack(">I", 2048))
            reader.feed_eof()
            with self.assertRaises(WireError):
                await read_cast_message(reader, max_size=1024)

        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
