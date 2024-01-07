"""
Pubnix Server/Client Library
Author: Brandon Rozek

The pubnix library contains server
and client code needed to communicate
over unix domain sockets on a single
machine.

For authentication, we rely on challenge
tokens and the unix permission system as
both server and client run on the same 
machine.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Union
import binascii
import json
import os
import pwd
import sys
import socket

__all__ = ['run_simple_server', 'run_simple_client']

MESSAGE_BUFFER_LEN = 1024
TOKEN_LENGTH = 50
TIMEOUT = 5 * 60 # 5 minutes

###
# Server
###

def run_simple_server(address, fn, force_auth=True):
    """
    This function can act as the main entrypoint
    for the server. It takes a function that interacts
    with a connected user (potentially authenticated)

    Example
    =======
    if __name__ == "__main__":
      run_simple_server(
        "/home/project/.pubnix.sock",
        lambda connection, user: connection.sendall(f"Hello {user}".encode())
      )
    """
    with start_server(address) as sock:
        print("Started server at", address)
        try:
            while True:
                connection, _ = sock.accept()
                connection.settimeout(TIMEOUT)
                t = Thread(target=thread_connection, args=[connection, force_auth, fn])
                t.daemon = True # TODO: Implement graceful cleanup instead
                t.start()
        except KeyboardInterrupt:
            print("Stopping server...")

def thread_connection(connection, force_auth, fn):
    try:
        user = None
        if force_auth:
            user = authenticate(connection)
        receive_message(connection, StartMessage)
        fn(connection, user)
    except (
        ProtocolException,
        BrokenPipeError,
        TimeoutError,
        ConnectionResetError) as e:
        # Ignore as client can reconnect
        pass
    finally: # clean up the connection
        if connection is not None:
            connection.close()

@contextmanager
def start_server(address, allow_other=True):
    """
    Opens up a unix domain socket at the specified address
    and listens for connections.

    allow_other: Allow other users on the system to connect
    to the unix domain socket
    """
    if os.path.exists(address):
        print(f"{address} exists -- server already running")
        sys.exit(1)
    
    # Create a unix domain socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(address)
    sock.listen()

    if allow_other:
        # 33279 = '-rwxrwxrwx.'
        os.chmod("game.sock", 33279)
        os.chmod("challenges", 33279)

    try:
        yield sock
    finally:
        # Delete game.sock when finished
        os.unlink(address)

def generate_challenge(user):
    SERVER_FOLDER = Path(__file__).parent.absolute()
    Path(f"{SERVER_FOLDER}/challenges").mkdir(mode=33279, exist_ok=True)
    return ChallengeMessage(
        username=user,
        token=generate_token(TOKEN_LENGTH),
        location=f"{SERVER_FOLDER}/challenges/.{user}_challenge"
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
        close_with_error(connection, f"Authentication Error: Challange file doesn't exist at {challenge.location}")
    
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

def generate_token(length):
    # From https://stackoverflow.com/a/41354711
    return binascii.hexlify(os.urandom(length // 2)).decode()

def find_owner(path: Union[str, Path]) -> str:
    return Path(path).owner()

###
# Client
###

def run_simple_client(address, fn, force_auth=True):
    """
    This function can act as the main entrypoint
    for the client. It takes a function that interacts
    with the server. If force_auth is enabled, then it
    first authenticates as the effect user running the
    program.

    Example
    =======
    if __name__ == "__main__":
      run_simple_client(
        "/home/project/.pubnix.sock",
        lambda connection, user: connection.sendall(f"Hello server, I'm {user}".encode())
      )
    """
    with start_client(address) as client:
        if force_auth:
            user, success = login(client)
        if not force_auth or success:
            send_message(client, StartMessage())
            fn(client, user)

@contextmanager
def start_client(address):
    # Create the Unix socket client
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Connect to the server
    try:
        client.connect(address)
    except FileNotFoundError:
        print("Server is not running at location", address)
        sys.exit(1)

    try:
        yield client
    finally:
        client.close()

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

    # On success, delete challenge file
    success = True
    try:
        message = receive_message(connection, AuthSuccessMessage)
    except ProtocolException as e:
        print(e)
        success = False
    finally:
        os.unlink(challenge.location)
    
    return user, success

##
# Messages
##

class MessageEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__ 

def send_message(connection, message):
    contents = json.dumps(message, cls=MessageEncoder).encode()
    connection.sendall(contents)

def receive_message(connection, cls=None):
    message = connection.recv(MESSAGE_BUFFER_LEN).decode()

    if len(message) == 0:
        raise ProtocolException("Sender closed the connection")

    try:
        message = json.loads(message)
    except Exception:
        close_with_error(connection, "Invalid Message Received")

    if cls is not None:
        try:
            message = cls(**message)
        except (TypeError, AssertionError):
            if "type" in message and message['type'] == "error":
                raise ProtocolException(message.get("message"))
            else:
                close_with_error(connection, f"Expected message of type {cls}")

    return message

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
