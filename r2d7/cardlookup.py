import copy
from html import unescape
from itertools import chain, groupby
import logging
import re

from r2d7.core import DroidCore, DroidException, long_substr

logger = logging.getLogger(__name__)


class CardLookup(DroidCore):
    def __init__(self):
        super().__init__()
        self.register_handler(r'\[\[(.*)\]\]', self.handle_lookup)
        self.register_dm_handler(r'(.*)', self.handle_lookup)

    _lookup_data = None

    _action_order = (
        'Focus',
        'Recover',
        'Reinforce',
        'Target Lock',
        'Barrel Roll',
        'Boost',
        'Evade',
        'Cloak',
        'Coordinate',
        'Jam',
        'SLAM',
        'Rotate Arc',
    )
    @classmethod
    def _action_key(cls, action):
        try:
            return cls._action_order.index(action)
        except ValueError:
            #TODO log an error?
            return 100

    _slot_order = (
        'Talent',
        'Force',
        'System',
        'Cannon',
        'Turret',
        'Torpedo',
        'Missile',
        'Crew',
        'Gunner',
        'Astromech Droid',
        'Device',
        'Illicit',
        'Modification',
        'Title',
        'Configuration',
        # 'Tech',
        # 'Hardpoint',
        # 'Team',
        # 'Cargo',
    )
    @classmethod
    def _slot_key(cls, slot):
        try:
            return cls._slot_order.index(slot)
        except ValueError:
            #TODO log an error?
            return 100

    _aliases = {
        'fcs': 'firecontrolsystem',
        'apl': 'antipursuitlasers',
        'atc': 'advancedtargetingcomputer',
        'ptl': 'pushthelimit',
        'hlc': 'heavylasercannon',
        'tlt': 'twinlaserturret',
        'vi': 'veteraninstincts',
        'at': 'autothrusters',
        'as': 'advancedsensors',
        'acd': 'advancedcloakingdevice',
        'eu': 'engineupgrade',
        'tap': 'tieadvancedprototype',
        'ac': 'accuracycorrector',
        'abt': 'autoblasterturret',
        'sd': 'stealthdevice',
        'ei': 'experimentalinterface',
        'k4': 'k4securitydroid',
        'stressbot': 'r3a2',
        'countesskturn': 'countessryad',
        'countesskturns': 'countessryad',
        'countessbluekturn': 'countessryad',
        'bmst': 'blackmarketslicertools',
        'snuggling': 'smugglingcompartment',
        'snugglingcompartment': 'smugglingcompartment',
    }

    def load_data(self):
        super().load_data()
        self._init_lookup_data()


    def _init_lookup_data(self):
        next_id = 0
        self._lookup_data = {}
        self._name_to_xws = {}
        for names in self.data.values():
            for cards in names.values():
                for card in cards:
                    name = self.partial_canonicalize(card['name'])
                    self._lookup_data.setdefault(name, []).append(card)
                    self._name_to_xws[card['name']] = card['xws']
                    card['_id'] = next_id
                    next_id += 1
        # for group in self._processing_order:
        #     cards = self.data[group]
        #     for name, cards in cards.items():
        #         for card in cards:
        #             if group == 'conditions':
        #                 card['slot'] = 'condition'
        #             elif group == 'ships':
        #                 card['slot'] = card['xws']
        #                 card['actions'].sort(key=self._action_key)
        #             elif 'damage-deck' in group:
        #                 card['slot'] = 'crit'
        #                 card['deck'] = 'TFA' if 'tfa' in group else 'Original'
        #             elif group == 'pilots':
        #                 ships = self._lookup_data[
        #                     self._name_to_xws[card['ship']]]
        #                 if len(ships) > 1:
        #                     raise DroidException(
        #                         f"Duplicate ship found: {ships}")
        #                 card['ship_card'] = ships[0]

        #                 # Add pilot to it's ship so we can list ship pilots
        #                 card['ship_card'].setdefault('pilots', []).append(
        #                     card)

        #                 if 'ship_override' in card:
        #                     card['ship_card'] = copy.copy(card['ship_card'])
        #                     card['ship_card'].update(card['ship_override'])

        #                 card['slots'].sort(key=self._slot_key)

        #                 # Give ship slots if it doesn't have them
        #                 try:
        #                     skill = int(card['skill'])
        #                     if card['ship_card'].get('_slot_skill', 13) > skill:
        #                         card['ship_card']['_slot_skill'] = skill
        #                         card['ship_card']['slots'] = card['slots']
        #                 except ValueError:
        #                     pass

        #                 card['slot'] = card['ship_card']['xws']

        #             card['_id'] = next_id
        #             card['_group'] = group
        #             next_id += 1
        #             self._lookup_data.setdefault(name, []).append(card)
        #             self._name_to_xws[card['name']] = card['xws']

    _multi_lookup_pattern = re.compile(r'\]\][^\[]*\[\[')
    @property
    def filter_pattern(self):
        raise NotImplementedError()

    def lookup(self, lookup):
        if self._lookup_data is None:
            self.load_data()

        lookup = unescape(lookup)
        logger.debug(f"Looking up: {repr(lookup)}")

        cards_yielded = set()
        for lookup in self._multi_lookup_pattern.split(lookup):
            matches = []
            slot_filter = None
            points_filter = None
            search = lookup
            match = self.filter_pattern.match(lookup)
            if not match:
                match = (None, None, lookup, None, None, None)
            slot_filter = match[1] or match[5]

            if match[2]:
                lookup = self.partial_canonicalize(match[2])
                if len(lookup) > 2 or re.match(r'[a-z]\d', lookup):
                    ex_lookup = match[2].lower().strip()
                    # We want "hot shot" to match "Hot Shot Blaster" and
                    # "Hotshot Co-pilot"
                    ex_lookup = re.sub(r' ', ' ?', ex_lookup)
                    exact = re.compile(
                        f'\\b{re.escape(ex_lookup)}(?:[\'e]?s)?\\b',
                        re.IGNORECASE
                    )
                    matches = [
                        key for key, cards in self._lookup_data.items() if any(
                            exact.search(card['name']) for card in cards
                        )
                    ]
                    if not matches:
                        matches = [key for key in self._lookup_data.keys()
                                   if lookup in key]
                if lookup in self._aliases:
                    matches.append(self._aliases[lookup])
            else:
                if not slot_filter:
                    raise DroidException(
                        'You need to specify a slot to search by points value.')
                matches = self._lookup_data.keys()
                operator = '==' if match[3] == '=' else match[3]
                operand = match[4]

                points_filter = lambda val: eval(f"{val}{operator}{operand}")

            for match in matches:
                for card in self._lookup_data[match]:
                    if card['_id'] in cards_yielded:
                        continue
                    if slot_filter and self.iconify(card['category']) != slot_filter:
                        continue
                    #TODO points filter
                    # if points_filter and not points_filter(card['cost']):
                    #     continue

                    cards_yielded.add(card['_id'])
                    yield card

                    if 'conditions' in card:
                        for condition in chain.from_iterable(
                                self.data['conditions'].values()):
                            if condition['_id'] in cards_yielded:
                                continue
                            if condition['name'] in card['conditions']:
                                yield condition
                                cards_yielded.add(condition['_id'])

    _arc_icons = {
        'Turret': 'turret',
        'Auxiliary Rear': 'frontback',
        'Auxiliary 180': '180',
        'Bullseye': 'bullseye',
    }

    def ship_stats(self, ship, pilot=None):
        line = []
        if pilot and 'faction' in pilot:
            line.append(self.iconify(pilot['faction']))

        stats = []
        if pilot:
            stats.append(self.iconify(f"initiative{pilot['initiative']}"))
        for stat in ship['stats']:
            stats.append(self.print_stat(stat))
        if pilot and 'charges' in pilot:
            pass #TODO (force too)
        line.append(''.join(stats))

        arcs = [self._arc_icons[arc] for arc in ship.get('firing_arcs', [])
                if arc in self._arc_icons]
        if arcs:
            line.append(''.join(
                self.iconify(f"attack-{arc}", special_chars=True)
                for arc in arcs))

        if 'actions' in ship:
            line.append('|'.join(
                self.print_action(action) for action in ship['actions']
            ))

        #TODO slots, not in data yet
        # slots = None
        # if pilot and 'slots' in pilot:
        #     slots = pilot['slots']
        # elif 'slots' in ship:
        #     slots = ship['slots']
        # if slots:
        #     line.append(''.join(self.iconify(slot) for slot in slots))

        return ' | '.join(line)

    # Dialgen format defined here: http://xwvassal.info/dialgen/dialgen
    maneuver_key = (
        ('T', 'turnleft'),
        ('B', 'bankleft'),
        ('F', 'straight'),
        ('N', 'bankright'),
        ('Y', 'turnright'),
        ('K', 'kturn'),
        ('L', 'sloopleft'),
        ('P', 'sloopright'),
        ('E', 'trollleft'),
        ('R', 'trollright'),
        ('A', 'reversebankleft'),
        ('S', 'reversestraight'),
        ('D', 'reversebankright'),
    )
    stop_maneuver = ('O', 'stop')

    difficulty_key = {
        'R': 'red',
        'W': '',
        'G': 'green',
        'B': 'blue',
    }

    def maneuvers(self, dial):
        used_moves = {move[1] for move in dial}
        dial = {speed: {move[1]: move[2] for move in moves}
                for speed, moves in groupby(dial, lambda move: move[0])}
        result = []
        blank = self.iconify('blank')
        for speed, moves in dial.items():
            line = [speed + ' ']
            for dialgen_move, droid_move in self.maneuver_key:
                if dialgen_move not in used_moves:
                    continue
                if speed == '0' and dialgen_move == 'F':
                    dialgen_move, droid_move = self.stop_maneuver
                if dialgen_move in moves:
                    line.append(self.iconify(
                        self.difficulty_key[moves[dialgen_move]] + droid_move
                    ))
                else:
                    line.append(blank)

            result.append(''.join(line))
        result.reverse()
        return result

    def pilot_ini_key(self, pilot):
        try:
            return int(pilot['initiative'])
        except ValueError:
            # Put ?s at the end
            return 9

    def list_pilots(self, ship):
        factions = {}
        for faction, pilots in ship['pilots'].items():
            pilots = sorted(pilots, key=self.pilot_ini_key)
            factions[faction] = []
            for pilot in pilots:
                init = self.iconify(f"initiative{pilot['initiative']}")
                unique = '• ' if pilot.get('limited', False) else ''
                # TODO, data is missing slots
                # elite = ' ' + self.iconify('elite') if 'Elite' in pilot['slots'] else ''
                elite = ''
                name = self.format_name(pilot)
                factions[faction].append(
                    f"{init}{unique}{name}{elite} [{pilot['cost']}]")
        return [f"{self.iconify(faction)} {', '.join(pilots)}"
                for faction, pilots in factions.items()]

    def format_name(self, card):
        # There's no wiki pages for ships or crits
        if card['category'] == 'ships' or card['category'] == 'damage':
            return card['name']
        else:
            return self.wiki_link(card['name'])
            #TODO handle special cases

    def print_action(self, action):
        difficulty = '' if action['difficulty'] == 'White' else action['difficulty']
        out = self.iconify(difficulty + action['type'])
        if 'linked' in action:
            out += self.iconify('linked') + self.print_action(action['linked'])
        return out

    stat_colours = {
        "attack": "red",
        "agility": "green",
        "hull": "yellow",
        "shield": "blue",
        "charge": "orange",
        "force": "purple",
    }

    def print_stat(self, stat):
        stat_type = stat['type']
        if stat_type == 'attack':
            out = self.iconify(f"red{stat['arc']}")
        else:
            if stat['type'] == 'shields':
                stat_type = 'shield'
            out = self.iconify(f"{self.stat_colours[stat_type]}{stat_type}")
        out += self.iconify(f"{stat_type}{stat['value']}")
        return out

    restriction_faction_map = {
        'Galactic Empire': 'Imperial',
        'Rebel Alliance': 'Rebel',
        'Scum and Villainy': 'Scum',
    }

    def print_restrictions(self, restrictions):
        out = []
        for restrict in restrictions:
            if 'action' in restrict:
                out.append(self.print_action(restrict['action']))
            if 'factions' in restrict:
                out.append(' or '.join(
                    self.restriction_faction_map[faction]
                    for faction in restrict['factions']
                ))
            if 'chassis' in restrict:
                out.append(' or '.join(
                    self.iconify(ship) for ship in restrict['chassis']
                ))
            if 'sizes' in restrict:
                out.append(' or '.join(restrict['sizes']) + ' ship')
        return 'Restrictions: ' + ' and '.join(out)

    def print_ship_ability(self, ability):
        lines = self.convert_html(ability['text'])
        lines[0] = self.italics(self.bold(ability['name'] + ':')) + ' ' + lines[0]
        return lines

    def print_card(self, card):
        is_ship = card['category'] == 'ship'
        is_pilot = card['category'] == 'pilot'

        if not is_ship and not is_pilot:
            front_side = card['sides'][0]
        else:
            front_side = {'slots': [
                card['xws'] if is_ship else card['ship']['xws']
            ]}

        text = []
        text.append(' '.join(filter(len, (
            ''.join(self.iconify(slot) for slot in front_side['slots']),
            '•' if card.get('limited', False) else '',
            self.bold(self.format_name(card)),
            f"[{card['points']}]" if 'points' in card else '',
            f"({card['deck']})" if 'deck' in card else '',
            self.iconify(f"{card['size']}base") if 'size' in card else '',
        ))))

        if 'restrictions' in card:
            text.append(self.print_restrictions(card['restrictions']))

        if is_pilot:
            text.append(self.ship_stats(card['ship_card'], card))
        elif is_ship:
            text.append(self.ship_stats(card))

        if 'ability' in front_side:
            text += self.convert_html(front_side['ability'])

        if 'text' in front_side:
            text.append(self.italics(front_side['text']))

        last_line = []
        if 'attack' in front_side:
            atk = front_side['attack']
            range_bonus = front_side['slots'] in (['Missile'], ['Torpedo'])
            last_line.append(
                self.iconify('red' + atk['arc']) +
                self.iconify(f"attack{atk['value']}") +
                (self.iconify('redrangebonusindicator') if range_bonus else '') +
                f"{atk['minrange']}-{atk['maxrange']}"
            )
        if 'charges' in front_side:
            charges = front_side['charges']
            last_line.append(
                self.iconify('orangecharge') +
                self.iconify(f"charge{charges['value']}") +
                (self.iconify('orangerecurring') if charges['recovers'] else ''))
        if 'force' in front_side:
            force = front_side['force']
            last_line.append(
                self.iconify('purpleforcecharge') +
                self.iconify(f"forceplus{force['value']}") +
                (self.iconify('purplerecurring') if force['recovers'] else ''))
        if 'actions' in front_side:
            last_line.append('|'.join(
                self.print_action(action) for action in front_side['actions']
            ))
        if last_line:
            text.append(' | '.join(last_line))

        if 'dial' in card:
            text += self.maneuvers(card['dial'])

        if 'pilots' in card:
            text += self.list_pilots(card)

        return text


    def handle_lookup(self, lookup):
        output = []
        count = 0
        for card in self.lookup(lookup):
            count += 1
            if count > 10:
                return ['Your search matched more than 10 cards, please be '
                        'more specific.']
            output += self.print_card(card)
        return output
