import os
import sys
from ansi_codes import ColorCodes
from datetime import datetime
import json
import logging
import socket
import select
from colorama import just_fix_windows_console


class SeaBot:
    class MultiFormatter(logging.Formatter):
        def format(self, record):
            color = ColorCodes.RESET
            if record.levelno == logging.ERROR:
                color = ColorCodes.ERROR
            elif record.levelno == logging.WARNING:
                color = ColorCodes.WARNING
            elif record.levelno == logging.DEBUG:
                color = ColorCodes.DEBUG
            return ''.join([
                '* ',
                datetime.fromtimestamp(record.created).strftime("%m/%d/%Y %I:%M:%S %p"),
                ': ',
                color,
                '[',
                record.levelname,
                '] ',
                record.msg,
                ColorCodes.RESET
            ])

    irc_client: socket.socket = None
    logger: logging.Logger = None
    nickname: str = None
    channel: str = None
    is_online: bool = False

    def __init__(self, debug: bool = False) -> None:
        self.irc_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger = self.__create_logger(debug)
        self.nickname = 'SeaBotBeepBoop'
        self.channel = '#smokedseabass'
        return
    
    def __create_logger(self, show_debug: bool = False) -> logging.Logger:
        just_fix_windows_console()
        logger = logging.getLogger(__name__)
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(self.MultiFormatter())
        logger.addHandler(log_handler)
        if show_debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        return logger

    def connect(self) -> bool:
        """
        Connects to Twitch IRC server and logs into bot account.
        
        Returns:
            `True` on success.  Otherwise, returns `False`.
        """
        # Connect to Twitch IRC server
        try:
            self.logger.info("Connecting to Twitch...")
            self.irc_client.connect(("irc.chat.twitch.tv", 6667))
        except Exception as ex:
            self.logger.error("Failed to connect to Twitch IRC server!")
            raise ex
        self.logger.info("Successfully connected to Twitch IRC server")

        # Log into Twitch bot account
        with open(os.path.abspath("./credentials/oauth_token.json"), 'r') as token_file:
            token: dict = json.load(token_file)
        self.irc_client.send(bytes("CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands\n", 'utf-8'))
        response = self.wait_for_twitch_response()
        for line in response:
            self.logger.debug(line.rstrip())
        self.irc_client.send(bytes(f"PASS oauth:{token.get('access_token')}\n", 'utf-8'))
        self.irc_client.send(bytes(f"NICK {self.nickname}\n", 'utf-8'))
        response = self.wait_for_twitch_response()
        for line in response:
            self.logger.debug(line.rstrip())
        if 'failed' in response or 'unsuccessful' in response:
            self.logger.error("Failed to log into account!")
            return False
        self.is_online = True
        self.logger.info(f'Successfully logged in as {self.nickname}')

        # Connect to my channel
        self.irc_client.send(bytes(f"JOIN {self.channel}\n", 'utf-8'))
        response = self.wait_for_twitch_response()
        for line in response:
            self.logger.debug(line.rstrip())
        self.irc_client.send(bytes(f"PRIVMSG {self.channel} :Beep boop, hello everyone!\n", 'utf-8'))
        return True

    def disconnect(self):
        """
        Disconnect from the Twitch IRC server.
        """
        self.irc_client.close()
        self.is_online = False
        self.logger.info("Disconnected from Twitch IRC server")
        return
    
    def wait_for_twitch_response(self, timeout: float | None = None) -> list[str]:
        """
        Listen for a message from the Twitch IRC server.

        Parameters:
            - timeout: How long to wait for a response, in seconds. Defaults to `None` (wait indefinitely).

        Returns:
            Decoded list of strings received from Twitch. `None` if no response received by timeout
        """
        response: list = []
        ready_sockets = select.select([self.irc_client], [], [], timeout)
        if ready_sockets[0]:
            response = [line for line in self.irc_client.recv(2048).decode('utf-8').split('\r\n') if line.strip() != '']
        return response
    
    def send_irc_message(self, irc_message: str):
        if not irc_message.endswith('\n'):
            irc_message += '\n'
        self.irc_client.send(bytes(irc_message, 'utf-8'))
        self.logger.info(irc_message)
        return
    
    def parse_irc_message(self, irc_message: str) -> dict:
        tags_component: str = None
        source_component: str = None
        command_component: str = None
        parameters_component: str = None
        parsed_irc_message: dict = {
            'tags': dict(),
            'source': dict(),
            'command': dict(),
            'parameters': []
        }
        component_start_index: int = 0
        # Extract tags component
        if (irc_message[component_start_index] == '@'):
            component_end_index: int = irc_message.find(' ')
            tags_component = irc_message[component_start_index:component_end_index]
            component_start_index = component_end_index + 1
        # Extract source component
        if (irc_message[component_start_index] == ':'):
            component_end_index: int = irc_message.find(' ', component_start_index)
            source_component = irc_message[component_start_index:component_end_index]
            component_start_index = component_end_index + 1
        # Extract command component
        component_end_index: int = irc_message.find(':', component_start_index)
        if (component_end_index == -1):
            component_end_index = len(irc_message)
        command_component = irc_message[component_start_index:component_end_index]
        # Extract parameter component
        if (component_end_index != len(irc_message)):
            component_start_index = component_end_index + 1
            parameters_component = irc_message[component_start_index:]
        self.logger.debug(f"Tags string: {tags_component}")
        self.logger.debug(f"Source string: {source_component}")
        self.logger.debug(f"Command string: {command_component}")
        self.logger.debug(f"Parameters string: {parameters_component}")




        if command_component.startswith('PRIVMSG'):
            pass
        elif command_component.startswith('PING'):
            self.irc_client.send(bytes('PONG :tmi.twitch.tv\n', 'utf-8'))
        return
    
    def parse_chat_message(self, chat_message: str):
        if chat_message.startswith('!'):
            chat_command: list[str] = chat_message[1:].split()
            match chat_command[0]:
                case 'ping':
                    self.send_chat_message("pong!")
        return
    
    def send_chat_message(self, string: str):
        irc_message: str = f"PRIVMSG {self.channel} :{string}\n"
        self.irc_client.send(bytes(irc_message, 'utf-8'))
        self.logger.info(irc_message)
        return


def main(args: list[str]):
    if '-v' in args:
        smokedseabot = SeaBot(debug=True)
    else:
        smokedseabot = SeaBot(debug=False)
    
    smokedseabot.connect()
    try:
        while smokedseabot.is_online:
            response = smokedseabot.wait_for_twitch_response(1.0)
            for line in response:
                if len(line) > 0:
                    smokedseabot.logger.info(line.rstrip())
                    smokedseabot.parse_irc_message(line)
    except KeyboardInterrupt:
        smokedseabot.logger.info("Shutting down...")
    finally:
        smokedseabot.disconnect()
    smokedseabot.logger.info("Goodbye!")


if __name__ == "__main__":
    main(sys.argv[1:])