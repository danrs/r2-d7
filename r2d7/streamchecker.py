from collections import OrderedDict
import logging
import re

from r2d7.core import DroidCore, DroidException

logger = logging.getLogger(__name__)


class StreamChecker(DroidCore):
    """
    Command for checking what X-Wing streams are live
    Adapted from dodgepong's stimbot
    https://github.com/dodgepong/stimbot/blob/master/scripts/hubot-stream-notifier.coffee
    """

    def __init__(self):
        super().__init__()
        pattern = re.compile("!(stream|dream|meme|scream|cream|creme|crème|beam|steam|scheme|team|theme|bream|seam|gleam)(s)?", re.I)
        self.register_handler(pattern, self.handle_stream_command)

    #TODO add twitch API
    _twitch_url = "https://api.twitch.tv/kraken/streams?game=Android%3A%20Netrunner"

    #TODO add youtube API and find out how to get these identifiers
    #TODO add channels
    _youtube_live_channels = [
        'UCT0_zqao2b2kJBe-bmF_0og',         # team covenant
        # Weekend Warlords?
        # Onyx squadron
    ]

    _command_to_live = {
        'beam': 'firing',
        'meme': 'dank',
        'theme': 'developing',
        'scheme': 'plotting',
        'creme': 'curdling',
        'crème': 'curdling',
        'team': 'playing',
        'steam': 'ironing',
    }

    def list_streams(self, command):
        logger.debug(f"Listing streams")
        live = self._command_to_live[command]
        twitch_streams = {} #TODO
        youtube_streams = {} #TODO
        num_streams = len(twitch_streams.keys()) + len(youtube_streams.keys())
        if num_streams == 0:
            logger.debug(f"No streams to list")
            message = f"No {plural} {are} {live} right now. :anakin:"
            return message
        else:
            logger.debug(f"{num_streams} streams are being listed")
            if num_streams > 1:
                plural = command + 's'
                are = 'are'
            else:
                plural = command
                are = 'is'

            message = f"{num_streams} {plural} {are} {live} right now:"
            # TODO append youtube and twitch channels to message
            return message

    def handle_stream_command(self, message):
        return self.list_streams(message)

