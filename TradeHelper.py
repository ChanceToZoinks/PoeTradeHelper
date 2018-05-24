from itertools import islice
import os
import threading
from time import sleep
from pyautogui import *
from Observable import *
from PoEApiTools import PoeApiTools as pat
import ctypes
import ctypes.wintypes
from subprocess import run
import json
from json import JSONEncoder
from json import JSONDecoder
import numpy as np

FAILSAFE = True
POEPATH = "E:\Games\Path of Exile\Path of Exile\PathOfExile.exe"
CLIENTPATH = "E:\Games\Path of Exile\Path of Exile\logs\Client.txt"
DIRNAME = os.path.dirname(__file__)
LEAGUE = 'Bestiary'
ACCTNAME = 'testaccount_aziz'


def rel_path(filename):
    return os.path.join(DIRNAME, 'Resources/{0}'.format(filename))


class Currency:
    def __init__(self, numCurrencyAvailable: int, maxInOneStack: int):
        self.count = numCurrencyAvailable
        self.stackSize = maxInOneStack


class Point:
    """2D point in space data structure."""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


# noinspection PyTypeChecker
class PointEncoder(JSONEncoder):
    """Custom encoder for Point data structs into nested dict for json storage.
       Pass as cls arg in json.dump to do Point(x,y) -> {'__type__': 'Point', 'x': #, 'y': #}"""

    def default(self, o):
        if isinstance(o, Point):
            if isinstance(o.x, np.generic) and isinstance(o.y, np.generic):
                # values returned by pyautogui's locate() functions are apparently of type numpy.int64
                return {'__type__': 'Point', 'x': np.asscalar(o.x), 'y': np.asscalar(o.y)}
            else:
                return {'__type__': 'Point', 'x': o.x, 'y': o.y}
        return JSONEncoder.default(self, o)


class PointDecoder(JSONDecoder):
    """Custom decoder to extract Point data struct from properly labeled dict structures from json files.
       Pass as cls arg in json.load to do {'__type__': 'Point', 'x': #, 'y': #} -> Point(x,y)"""

    def __init__(self, *args, **kwargs):
        JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, o):
        if '__type__' not in o:
            return o
        if '__type__' in o and o['__type__'] == 'Point':
            return Point(o['x'], o['y'])
        return o


class CentralControl(Observer):
    """This is the central event handler. It holds the references for each of the five bots and contains callbacks
       necessary to maintain the correct order of events and to ensure trades are being completed."""

    def __init__(self, league=LEAGUE, interval=1):
        # Observer's init needs to be called
        Observer.__init__(self)

        self.interval = interval
        self.parser = MessageParserBot()
        self.finder = FinderBot()
        self.trader = TradeBot()
        self.messenger = MessengerBot()
        self.inventory = InventoryManagerBot()

        # opens poe and gets the hwnd and makes poe foreground/active window
        win = getWindow("Path of Exile")
        if win is None:
            try:
                run(POEPATH)
                win = getWindow("Path of Exile")
            except FileNotFoundError:
                print("Can't find PoE executable. Check your POEPATH.")
        ctypes.windll.user32.SwitchToThisWindow(win._hwnd)
        win.set_foreground()

        self.league = league
        # holds the list of all new messages seens so they can be processed sequentially
        self.tradeList = []
        # all ratios listed in chaos equiv
        self.sellRatios = {'alteration': 1, "jeweller's": 1, 'fusing': 1, "exalted": 1, "chance": 1, "chrome": 1,
                           'gcp': 1, 'alchemy': 1, 'chisel': 1, 'scouring': 1, 'regal': 1, 'regret': 1, 'divine': 1,
                           'vaal': 1}

        self.observe('new message', self.new_trade_message_received)
        self.observe('new command', self.new_command_message_received)

        trade_work_thread = threading.Thread(target=self.work_trade_list)
        trade_work_thread.daemon = True
        trade_work_thread.start()

    def work_trade_list(self):
        while True:
            if len(self.tradeList) > 0:
                # if the trade list contains anything deal with them sequentially
                self.transact_trade(self.tradeList.pop(0))

    def transact_trade(self, tradeData: dict):
        """Handles the trading by calling the appropriate methods in the bots"""

        # first check to be sure we even have the item

        # if we dont have the item inform the player otherwise invite them

        # click the correct screen locations to complete the trade

    def new_trade_message_received(self, messageData: dict):
        """Callback for trade message being received. Appends the trade to the list if the ratio offered is correct."""

        print(messageData)
        if self.ratio_checker(itemName=messageData['itemName'],
                              itemQuant=messageData['itemQuant'],
                              offer=messageData['offerQuant']):
            # ratio matches so append to the trade queue and begin the the trade sequence
            self.tradeList.append(messageData)

    def new_command_message_received(self, command: str):
        """Callback for command received."""

        print(command)

    def ratio_checker(self, itemName: str, itemQuant: float, offer: float) -> bool:
        """Checks the ratio of chaos offered/items requested to make sure they match the ratio we selling at"""

        return float(offer)/float(itemQuant) == self.sellRatios[itemName]


class TradeBot:
    """Handles collecting the currency and trading the correct person in addition to kicking, changing hideouts.
       Holds methods to perform chat console commands and click the mouse at the correct locations."""

    def __init__(self):
        print('Initializing trade bot...')
        print('Trade bot initialized.')

    def click(self, point: Point, button='left'):
        """Regular old click at the location specified by the point. button=['left'|'right'|'middle']."""

        click(x=point.x, y=point.y, button=button)

    def shift_click(self, point: Point):
        """Ctrl+left clicks at a location. Point is of type Point."""

        keyDown('shift')
        click(x=point.x, y=point.y)
        keyUp('shift')

    def control_click(self, point: Point):
        """Ctrl+left clicks at a location."""

        keyDown('ctrl')
        click(x=point.x, y=point.y)
        keyUp('ctrl')

    def invite_player(self, playerName: str):
        """Handles inviting the correct player to the group."""

        press('enter')
        typewrite('/invite {0}'.format(playerName))
        press('enter')

    def kick_player(self, playerName: str):
        """Handles kicking players."""

        press('enter')
        typewrite('/kick {0}'.format(playerName))
        press('enter')

    def init_trade(self, playerName: str):
        """Handles initiation of trade with a player."""

        press('enter')
        typewrite('/tradewith {0}'.format(playerName))
        press('enter')

    def go_hideout(self, playerName: str):
        """Handles travelling to hideouts."""

        press('enter')
        typewrite('/hideout {0}'.format(playerName))
        press('enter')


class FinderBot:
    """Handles locating the on screen coordinates of the currency in the currency tab for the trade bot."""

    def __init__(self):
        print('Initializing finder bot...')

        self.currencyImages = {'wisdom': rel_path('wisdom.png'),
                               'portal': rel_path('portal.png'),
                               'alchemy': rel_path('alchemy.png'),
                               'alteration': rel_path('alteration.png'),
                               'annul': rel_path('annul.png'),
                               'armorer': rel_path('armorer.png'),
                               'augmentation': rel_path('augmentation.png'),
                               'bauble': rel_path('bauble.png'),
                               'blessed': rel_path('blessed.png'),
                               'chance': rel_path('chance.png'),
                               'chaos': rel_path('chaos.png'),
                               'chisel': rel_path('chisel.png'),
                               'chromatic': rel_path('chromatic.png'),
                               'divine': rel_path('divine.png'),
                               'exalt': rel_path('exalt.png'),
                               'exalt shard': rel_path('exaltShard.png'),
                               'fusing': rel_path('fusing.png'),
                               'gcp': rel_path('gcp.png'),
                               'jeweller': rel_path('jeweller.png'),
                               'mirror of kalandra': rel_path('mirror.png'),
                               'perandus coin': rel_path('perandusCoin.png'),
                               'master sextant': rel_path('redSextant.png'),
                               'regal': rel_path('regal.png'),
                               'regret': rel_path('regret.png'),
                               'scouring': rel_path('scouring.png'),
                               'silver coin': rel_path('silverCoin.png'),
                               'transmutation': rel_path('transmutation.png'),
                               'vaal': rel_path('vaal.png'),
                               'whetstone': rel_path('whetstone.png'),
                               'apprentice sextant': rel_path('whiteSextant.png'),
                               'journeyman sextant': rel_path('yellowSextant.png')}
        self.currencyLocations = {'scroll of wisdom': None,
                                  'portal scroll': None,
                                  'orb of alchemy': None,
                                  'orb of alteration': None,
                                  'orb of annulment': None,
                                  "armourer's scrap": None,
                                  'orb of augmentation': None,
                                  "glassblower's bauble": None,
                                  'blessed orb': None,
                                  'orb of chance': None,
                                  'chaos orb': None,
                                  "cartographer's chisel": None,
                                  'chromatic orb': None,
                                  'divine orb': None,
                                  'exalted orb': None,
                                  'exalted shard': None,
                                  'orb of fusing': None,
                                  "gemcutter's prism": None,
                                  "jeweller's orb": None,
                                  'mirror of kalandra': None,
                                  'perandus coin': None,
                                  "master cartographer's sextant": None,
                                  'regal orb': None,
                                  'orb of regret': None,
                                  'orb of scouring': None,
                                  'silver coin': None,
                                  'orb of transmutation': None,
                                  'vaal orb': None,
                                  "blacksmith's whetstone": None,
                                  "apprentice cartographer's sextant": None,
                                  "journeyman cartographer's sextant": None}
        self.stashImages = {'stash0': rel_path('stash0.png'),
                            'stash1': rel_path('stash1.png')}
        self.guildStashImages = {'guildStash0': rel_path('guildStash0.png'),
                                 'guildStash1': rel_path('guildStash1.png')}
        print('Finder bot initialized.')

    def find_currency_slots(self, confidence=.95):
        """Should only be called when currency tab is completely empty (eg start of league/account).
           Runs perfectly when tested on 1920x1080 screen."""

        for img in self.currencyImages:
            p = Point(0, 0)
            # pyautogui has undocumented confidence parameter for locate function
            p.x, p.y = locateCenterOnScreen(self.currencyImages[img], confidence=confidence)
            self.currencyLocations[img] = p
        with open('currencyStashLocations.json', 'w') as f:
            json.dump(obj=self.currencyLocations, fp=f,
                      cls=PointEncoder, indent=4, sort_keys=True)

    def find_stash(self, confidence=.9, guild=False) -> Point:
        """Attempts to locate the stash indicator. Returns when it does.
        MUST HAVE ALT CLICKED IN GAME SO "STASH" AND "GUILD STASH" LABELS ARE SHOWING.
        Appears to work perfectly at 1920x1080 resolution with max graphics settings in fullscreen and at max zoom."""

        loc = Point(0, 0)
        if guild:
            try:
                loc.x, loc.y = locateCenterOnScreen(self.guildStashImages['guildStash0'], confidence=confidence)
            except TypeError:
                print('Guild stash not found trying next image...')
            else:
                return loc
        else:
            try:
                loc.x, loc.y = locateCenterOnScreen(self.stashImages['stash0'], confidence=confidence)
            except TypeError:
                print("Stash not found maybe confidence is too high?")
            else:
                return loc

    def confirm_in_stash(self, confidence=.95, guild=False) -> bool:
        """Looks for a specific image to confirm we have indeed opened the stash.
           Confidence levels somewhere between .9 and .95 fail to differentiate between guild and regular stash."""

        if guild:
            check = locateOnScreen(self.guildStashImages['guildStash1'], confidence=confidence, grayscale=True)
            return bool(check)
        else:
            check = locateOnScreen(self.stashImages['stash1'], confidence=confidence, grayscale=True)
            return bool(check)


class MessengerBot:
    """Handles response to messages including commands sent to the central command"""

    def __init__(self):
        print('Initializing messenger bot...')

        print('Messenger bot initialized.')

    def build_message(self, target: str, message: str) -> str:
        """Returns a trade messsage in the form @['Playername'] ['message']"""

        return "@{0} {1}".format(target, message)

    def send_message(self, message: str):
        """Handles messaging players."""

        press('enter')
        typewrite(message)
        press('enter')


class InventoryManagerBot:
    """Handles inventory management"""

    def __init__(self):
        print('Initializing inventory manager bot...')

        self.stashed_currency = {'scroll of wisdom': 0,
                                 'portal scroll': 0,
                                 'orb of alchemy': 0,
                                 'orb of alteration': 0,
                                 'orb of annulment': 0,
                                 "armourer's scrap": 0,
                                 'orb of augmentation': 0,
                                 "glassblower's bauble": 0,
                                 'blessed orb': 0,
                                 'orb of chance': 0,
                                 'chaos orb': 0,
                                 "cartographer's chisel": 0,
                                 'chromatic orb': 0,
                                 'divine orb': 0,
                                 'exalted orb': 0,
                                 'exalted shard': 0,
                                 'orb of fusing': 0,
                                 "gemcutter's prism": 0,
                                 "jeweller's orb": 0,
                                 'mirror of kalandra': 0,
                                 'perandus coin': 0,
                                 "master cartographer's sextant": 0,
                                 'regal orb': 0,
                                 'orb of regret': 0,
                                 'orb of scouring': 0,
                                 'silver coin': 0,
                                 'orb of transmutation': 0,
                                 'vaal orb': 0,
                                 "blacksmith's whetstone": 0,
                                 "apprentice cartographer's sextant": 0,
                                 "journeyman cartographer's sextant": 0}

        print('Inventory manager bot initialized.')

    def check_stashed_currency(self):
        stash = pat.GGGGetPlayerStash(league=LEAGUE, accountName=ACCTNAME, tabs=0, tabIndex=0)
        for item in stash['items']:
            itemName = item['typeLine'].lower()
            if itemName in self.stashed_currency:
                stackSize = int(item['properties'][0]['values'][0][0].split('/')[1])
                self.stashed_currency[itemName] = Currency(item['stackSize'], stackSize)

    def get_currency_count(self, currency: str) -> int:
        return self.stashed_currency[currency].count

    def get_currency_stack_size(self, currency: str) -> int:
        return self.stashed_currency[currency].stackSize


class MessageParserBot:
    """Handles parsing of messages for the trade bot to use"""

    def __init__(self, interval=1):
        print('Initializing message parser bot...')
        self.interval = interval
        # holds the most recent message seen
        self.lastMessage = []
        self.parsedMessage = {}
        thread1 = threading.Thread(target=self.monitor_client_text)
        thread1.daemon = True
        thread1.start()
        print('Message parser bot initialized.')

    tradeKey1 = "Hi, I'd like to buy your"
    tradeKey2 = "Hi, I would like to buy your"
    commandKey1 = "Execute66:"

    def reversed_lines(self, file):
        """Generate the lines of file in reverse order."""

        part = ''
        for block in self.reversed_blocks(file):
            for c in reversed(block):
                if c == '\n' and part:
                    yield part[::-1]
                    part = ''
                part += c
        if part:
            yield part[::-1]

    def reversed_blocks(self, file, blocksize=4096):
        """Generate blocks of file's contents in reverse order."""

        file.seek(0, os.SEEK_END)
        here = file.tell()
        while 0 < here:
            delta = min(blocksize, here)
            here -= delta
            file.seek(here, os.SEEK_SET)
            yield file.read(delta)

    def check_last_line(self, file, key: str, key2: str, key3: str):
        """searches the last line of the file for the search strings and sends it to the parser method"""

        for line in islice(self.reversed_lines(file), 1):
            s = line.rstrip('\n')
            if key in s or key2 in s:
                self.parse_trade_message(s)
            elif key3 in s:
                self.parse_command_message(s)

    def monitor_client_text(self):
        with open(CLIENTPATH) as clientFile:
            while True:
                # if the string is found parse it to extract necessary info
                self.check_last_line(file=clientFile, key=self.tradeKey1, key2=self.tradeKey2, key3=self.commandKey1)

                sleep(self.interval)

    def new_line(self, message: str):
        """Handles making sure we don't needlessly send the same message to the central control"""

        if message == self.lastMessage:
            return False
        else:
            self.lastMessage = message
            return True

    # noinspection PyTypeChecker
    def parse_command_message(self, message: str):
        """Handles incoming commands sent through the game"""

        m = message.split('@')[1].split(' ')

        if self.new_line(m):
            if 'from' in m[0].lower():
                # incoming command found determine what it is and send the appropriate message
                for x in range(len(m)):
                    if self.commandKey1 in m[x]:
                        Event('new command', m[x+1])

    # noinspection PyTypeChecker
    def parse_trade_message(self, message: str):
        """
        First, determines whether a trade is actually incoming by splitting and looking for "From"
        If the trade is determined to be incoming then extracts:
                -the person making the offer
                -what they want
                -their offer
                -the league they are in
        that info is sent to the central control in the form of a list:
                {name, itemName, itemQuant, offerName, offerQuant, league}
        """

        m = message.split('@')[1].split(' ')

        # check to be sure we haven't already seen this line and detect if trade incoming
        if self.new_line(m) and 'from' in m[0].lower():
            # incoming trade found, begin extracting useful info
            # the offset is either 1 or 0 to account for the position of the guild tag because
            # m is a list in the form of [@From, GuildTag, PlayerName, word1, word2, ...]
            # sometimes the guildtag isn't present so this if statement checks for that
            if '<' in m[1] and '>' in m[1]:
                offset = 1
            else:
                offset = 0
            playerName = m[1 + offset]
            itemQuant = m[8 + offset]
            itemName = m[9 + offset]
            offerQuant = m[12 + offset]
            offerName = m[13 + offset]
            league = m[15 + offset]

            self.parsedMessage = {'playerName': playerName,
                                  'itemName': itemName, 'itemQuant': itemQuant,
                                  'offerName': offerName, 'offerQuant': offerQuant,
                                  'league': league}
            Event('new message', self.parsedMessage)
