from collections import OrderedDict
import logging
import re

from r2d7.core import DroidCore, DroidException

logger = logging.getLogger(__name__)


class FactionLister(DroidCore):
    @property
    def faction_icon_pattern(self):
        raise NotImplementedError()

    def __init__(self):
        super().__init__()
        pattern = re.compile(self.faction_icon_pattern, re.I)
        self.register_dm_handler(pattern, self.handle_faction_icon)

    icon_to_faction = {
        'scum': ('Scum and Villainy', ),
        'rebel': ('Rebel Alliance', 'Resistance'),
        'imperial': ('Galactic Empire', 'First Order'),
        'resistance': ('Resistance', ),
        'first_order': ('First Order', ),
    }

    def print_faction_ships(self, icon):
        logger.debug(f"Listing {icon}")
        try:
            factions = self.icon_to_faction[icon]
        except KeyError:
            logger.debug(f"{icon} is not a faction.")
            return []

        logger.debug(f"Listing ships in {', '.join(factions)}")
        # Use an OrderedDict as an ordered set
        ships = OrderedDict(
            (self.iconify(ship['xws']), None) for ship in self.raw_data['ships']
            for faction in ship['faction']
            if faction in factions and ship['size'] != 'huge'
        )

        return [''.join(ships)]

    def handle_faction_icon(self, message):
        return self.print_faction_ships(message)