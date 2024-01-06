"""
Author: Brandon Rozek

TODO: Handle a user trying to connect multiple
times at the same time. 

This might be handled automatically if only one
user can play at a time...
"""

import json
import pwd
import os
import sys
import socket
import binascii
from pathlib import Path
from typing import Union
from contextlib import contextmanager
from dataclasses import dataclass

# __all__ = ['send_message', 'MESSAGE_BUFFER_LEN', 'ChallengeMessage']

MESSAGE_BUFFER_LEN = 1024
TOKEN_LENGTH = 50
TIMEOUT = 5 * 60 # 5 minutes



@contextmanager
def start_client(address):
    # Create the Unix socket client
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Connect to the server
    try:
        client.connect(address)
    except FileNotFoundError:
        print("Game server is not running at location", address)
        sys.exit(1)

    try:
        yield client
    finally:
        client.close()



def run_simple_client(address, fn, force_auth=True):
    with start_client(address) as client:
        if force_auth:
            user = login(client)
        send_message(client, StartMessage())
        fn(client, user)

@contextmanager
def client_connection(sock):
    connection, _ = sock.accept()
    try:
        yield connection
    except (
        ProtocolException,
        BrokenPipeError,
        TimeoutError,
        ConnectionResetError) as e:
        # Ignore as client can reconnect
        pass
    finally: # clean up the connection
        connection.close()


def run_simple_server(address, fn, force_auth=True):
    with start_server(address) as sock:
        print("Started server at", address)
        try:
            while True:
                with client_connection(sock) as connection:
                    user = None
                    if force_auth:
                        user = authenticate(connection)
                    receive_message(connection, StartMessage)
                    fn(connection, user)
        except KeyboardInterrupt:
            print("Stopping server...")


def generate_token(length):
    # From https://stackoverflow.com/a/41354711
    return binascii.hexlify(os.urandom(length // 2)).decode()

def find_owner(path: Union[str, Path]) -> str:
    return Path(path).owner()

def generate_challenge(user):
    return ChallengeMessage(
        username=user,
        token=generate_token(TOKEN_LENGTH),
        location=f"/home/{user}/.pubnix_challenge"
    )

def authenticate(connection):
    # First message should be an authentication message
    message = receive_message(connection, AuthenticateMessage)
    user = message.username

    # Send challenge message
    challenge = generate_challenge(user)
    send_message(connection, challenge)

    # Second message should be validation message
    message = receive_message(connection, ValidationMessage)

    # Check that challenge file exists
    if not os.path.exists(challenge.location):
        close_with_error(connection, "Challange file doesn't exist")
    
    # Check if user owns the file
    if find_owner(challenge.location) != user: 
        close_with_error(connection, "Challange file not owned by user")
    
    # Make sure we can read the file
    if not os.access(challenge.location, os.R_OK):
        close_with_error(connection, "Challange file cannot be read by server")

    # Check contents of challenge file
    with open(challenge.location, "r") as file:
        contents = file.read()
    if contents != challenge.token:
        close_with_error(connection, "Token within challange file is incorrect")

    # Send authentication successful message
    send_message(connection, AuthSuccessMessage())
    return user

MESSAGE_BUFFER_LEN = 1024

def login(connection):
    # Send authentication message
    user = pwd.getpwuid(os.geteuid()).pw_name
    message = AuthenticateMessage(username=user)
    send_message(connection, message)

    # Receive challenge message
    challenge = receive_message(connection, ChallengeMessage)

    # Write to challenge file
    with open(challenge.location, "w") as file:
        file.write(challenge.token)
    
    # Tell server to check the challenge file
    send_message(connection, ValidationMessage())

    try:
        message = receive_message(connection, AuthSuccessMessage)
    finally:
        # Delete challenge file
        os.unlink(challenge.location)
    
    return user


class MessageEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__ 

def send_message(connection, message):
    contents = json.dumps(message, cls=MessageEncoder).encode()
    connection.sendall(contents)

def receive_message(connection, cls=None):
    message = connection.recv(MESSAGE_BUFFER_LEN).decode()
    try:
        message = json.loads(message)
    except Exception:
        print("Received:", message, flush=True)
        close_with_error(connection, "Invalid Message Received")

    if cls is not None:
        try:
            message = cls(**message)
        except (TypeError, AssertionError):
            close_with_error(connection, "Expected message of type")

    return message

@contextmanager
def start_server(address):
    if os.path.exists(address):
        print("game.sock exists -- game server already running")
        sys.exit(1)
    
    # Create a unix domain socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    sock.bind(address)
    sock.listen()

    try:
        yield sock
    finally:
        # Delete game.sock when finished
        os.unlink(address)


class ProtocolException(Exception):
    pass

def close_with_error(connection, content: str):
    message = dict(type="error", message=content)
    connection.sendall(json.dumps(message).encode())
    raise ProtocolException()


@dataclass
class ChallengeMessage:
    username: str
    token: str
    location: str
    action: str = "challenge"

    def __post_init__(self):
        assert self.action == "challenge"

@dataclass
class AuthenticateMessage:
    username: str
    action: str = "authenticate"

    def __post_init__(self):
        assert self.action == "authenticate"
        assert len(self.username) > 0

@dataclass
class ValidationMessage:
    action: str = "validate"
    def __post_init__(self):
        assert self.action == "validate"

@dataclass
class AuthSuccessMessage:
    type: str = "authentication_success"
    def __post_init__(self):
        assert self.type == "authentication_success"


@dataclass
class StartMessage:
    action: str = "start"
    def __post_init__(self):
        assert self.action == "start"
