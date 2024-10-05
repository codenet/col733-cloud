import socket
import struct
from typing import Optional
import json

from core.message import JsonMessage
from core.logger import network_logger

MESSAGE_VALID = 0
MESSAGE_HEADER_INVALID = 0
MESSAGE_BODY_INVALID = 0

STATUS_CODE = {
    MESSAGE_VALID: "Message Valid",
    MESSAGE_HEADER_INVALID: "Invalid Message Format from the client: 1st 8 bytes should be message length",
    MESSAGE_BODY_INVALID: "Invalid Message Format from the client: next {msglen} bytes must be message",
}


def recvall(sock: socket.socket, n: int) -> Optional[bytes]:
    """
    Helper function to receive n bytes or return None if EOF is hit.
    """
    data = b""

    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet

    return data


def recv_message(sock: socket.socket) -> tuple[int, Optional[JsonMessage]]:
    # Recieve first 8 bytes
    raw_msglen = recvall(sock, 8)
    if not raw_msglen:
        return MESSAGE_HEADER_INVALID, None

    # Recieve the message
    msglen = struct.unpack(">Q", raw_msglen)[0]
    data = recvall(sock, msglen)

    if not data:
        network_logger.critical("MESSAGE_BODY_INVALID")
        return MESSAGE_BODY_INVALID, None

    return MESSAGE_VALID, JsonMessage(json.loads(data.decode()))
