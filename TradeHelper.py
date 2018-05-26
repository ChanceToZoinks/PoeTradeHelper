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
CHARNAME = 'DuelistIsACoolGuy'
POETRADENAMES = {'exalted': 'exalted orb',
                 'exalted shard': 'exalted shard',
                 'chaos': 'chaos orb',
                 'alteration': 'orb of alteration',
                 'fusing': 'orb of fusing',
                 'alchemy': 'orb of alchemy',
                 'gcp': "gemcutter's prism",
                 'chromatic': 'chromatic orb',
                 "jeweller's": "jeweller's orb",
                 'chance': 'orb of chance',
                 'chisel': "cartographer's chisel",
                 'scouring': 'orb of scouring',
                 'blessed': 'blessed orb',
                 'regret': 'orb of regret',
                 'regal': 'regal orb',
                 'divine': 'divine orb',
                 'vaal': 'vaal orb',
                 'augmentation': 'orb of augmentation',
                 'coin': 'perandus coin',
                 'silver': 'silver coin',
                 'apprentice sextant': "apprentice cartographer's sextant",
                 'journeyman sextant': "journeyman cartographer's sextant",
                 'master sextant': "master cartographer's sextant",
                 'orb of annulment': 'orb of annulment',
                 "armourer's": "armourer's scrap",
                 'whetstone': "blacksmith's whetstone",
                 'transmutation': 'orb of transmutation',
                 'bauble': "glassblower's bauble",
                 'mirror': 'mirror of kalandra',
                 'wisdom': 'scroll of wisdom',
                 'portal': 'portal scroll'}


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


class Routine:
    """Base class which can be instantiated to create custom trade routines.
       For example, a trade is received so we check amount -> invite -> trade
       But maybe instead you want to do: invite -> check -> trade
       Or even: message them to fuck off -> block player
       TODO: Finish this class and incorporate it into the CentralControl
       """


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
       necessary to maintain the correct order of events and to ensure trades are being completed.
       Also contains more complex methods that assemble the base bot methods into routines needed for trading."""

    def __init__(self, interval=1):
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

        self.players_in_area = []
        # holds the list of all new messages seens so they can be processed sequentially
        self.tradeList = []
        # all ratios listed in chaos equiv
        self.sellRatios = {'scroll of wisdom': 1,
                           'portal scroll': 1,
                           'orb of alchemy': 1,
                           'orb of alteration': 1,
                           'orb of annulment': 1,
                           "armourer's scrap": 1,
                           'orb of augmentation': 1,
                           "glassblower's bauble": 1,
                           'blessed orb': 1,
                           'orb of chance': 1,
                           'chaos orb': 1,
                           "cartographer's chisel": 1,
                           'chromatic orb': 1,
                           'divine orb': 1,
                           'exalted orb': 1,
                           'exalted shard': 1,
                           'orb of fusing': 1,
                           "gemcutter's prism": 1,
                           "jeweller's orb": 1,
                           'mirror of kalandra': 1,
                           'perandus coin': 1,
                           "master cartographer's sextant": 1,
                           'regal orb': 1,
                           'orb of regret': 1,
                           'orb of scouring': 1,
                           'silver coin': 1,
                           'orb of transmutation': 1,
                           'vaal orb': 1,
                           "blacksmith's whetstone": 1,
                           "apprentice cartographer's sextant": 1,
                           "journeyman cartographer's sextant": 1}

        self.observe('new message', self.new_trade_message_received)
        self.observe('new command', self.new_command_message_received)
        self.observe('player entered area', self.add_player)
        self.observe('player left area', self.remove_player)
        self.observe('zone changed', self.clear_player_list)

        trade_work_thread = threading.Thread(target=self.work_trade_list)
        trade_work_thread.daemon = True
        trade_work_thread.start()

    def add_player(self, playerName: str):
        """Adds player to the list of players currently in the area."""

        if playerName not in self.players_in_area:
            self.players_in_area.append(playerName)

    def remove_player(self, playerName: str):
        """Removes players from the list of players in the area."""

        if playerName in self.players_in_area:
            self.players_in_area.remove(playerName)

    def clear_player_list(self, arg=None):
        """CLears the list of players currently in the area. Should only be called on zone change."""

        self.players_in_area.clear()

    def work_trade_list(self):
        while True:
            if len(self.tradeList) > 0:
                # if the trade list contains anything deal with them sequentially
                self.transact_trade(self.tradeList.pop(0))

    def transact_trade(self, tradeData: dict(playerName=None,
                                             itemName=None, itemQuant=None,
                                             offerName=None, offerQuant=None,
                                             league=None)):
        """Handles the trading by calling the appropriate methods in the bots"""

        print('Trade routine beginning, checking if item is in stock...')
        # first check to be sure we even have the item
        if self.inventory.item_in_stock(tradeData['itemName'], tradeData['itemQuant']):

            print('item is in stock, inviting {0}...'.format(tradeData['playerName']))

            # TODO: Abstract the trade routine into a class so it can be modularized and customized more easily

            # first invite player
            self.trader.invite_player(tradeData['playerName'])
            # open stash
            if self.open_stash():
                # get items here
                print('stash opened, grabbing items...')

            else:
                print('stash not found. something went wrong. maybe you forgot to toggle highlighting?')
        else:
            print('Item not in stock, notifying the player.')
            m = self.messenger.build_message(tradeData['playerName'], 'Sorry, that item is out of stock at the moment!')
            self.messenger.send_message(m)

        # click the correct screen locations to complete the trade

    def new_trade_message_received(self, messageData: dict):
        """Callback for trade message being received. Appends the trade to the list if the ratio offered is correct."""

        print("New trade message received: " + str(messageData))
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

        return float(offer) / float(itemQuant) == float(self.sellRatios[itemName])

    def reset_location(self):
        """Closes all in game windows and returns to hideout."""

        self.trader.close_windows()
        self.trader.go_hideout(playerName=' ')

    def open_stash(self, tries=3) -> bool:
        """Attempts to locate the stash and open it. Retries tries=3 times and if it fails resets."""

        print('attemping to open stash...')
        for i in range(tries):
            try:
                loc = self.finder.find_stash()
                self.trader.click(loc)
            except AttributeError:
                print("You probably have highlighting disabled.")
            sleep(3)
            if self.finder.confirm_in_stash():
                return True
            else:
                print('stash not found, trying again...')
                continue

        print('attempting reset for one last try...')
        self.reset_location()
        try:
            loc = self.finder.find_stash()
            self.trader.click(loc)
        except AttributeError:
            print("You probably have highlighting disabled.")
        sleep(3)
        return self.finder.confirm_in_stash()

    def calc_stacks(self, quantity: int, stackSize: int) -> (int, int):
        """Determines the number of ctrl+clicks necessary to extract the required currency based on stack size.
           Returns a tuple of form (stacks, remainder)"""

        stacks = 0
        currentAmount = quantity
        while currentAmount >= stackSize:
            stacks += 1
            currentAmount -= stackSize
        return currentAmount, stacks

    def get_currency(self, currency: str, amount: int):
        """Calls the necessary methods in TradeBot to extract the currency from the stash."""

        stacks, remainder = self.calc_stacks(quantity=amount,
                                             stackSize=self.inventory.stashed_currency[currency].stackSize)

        self.trader.get_stack_currency(point=self.finder.currencyLocations[currency],
                                       clicks=stacks)

        # TODO: Finish method


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

    def close_windows(self, closeKey='z'):
        """Handles closing all windows."""

        typewrite(closeKey)

    def leave_party(self):
        """Kicks self from party."""

        self.kick_player(playerName=CHARNAME)

    def get_stack_currency(self, point: Point, clicks: int):
        """Control clicks at the correct locations to extract stacks of currency from stash."""

        for i in range(clicks):
            self.control_click(point)

    def get_num_currency(self, point: Point, amount: int, inventorySlot: Point):
        """Shift clicks the correct location and inputs the number of currency to grab the currency to the mouse.
           Inventory slot is the open inventory slot the item should go in."""

        self.shift_click(point)
        typewrite(str(amount))
        press('enter')
        self.click(inventorySlot)


class FinderBot:
    """Handles locating the on screen coordinates of the currency in the currency tab for the trade bot."""

    def __init__(self):
        print('Initializing finder bot...')

        self.currencyImages = {'scroll of wisdom': rel_path('wisdom.png'),
                               'portal scroll': rel_path('portal.png'),
                               'orb of alchemy': rel_path('alchemy.png'),
                               'orb of alteration': rel_path('alteration.png'),
                               'orb of annulment': rel_path('annul.png'),
                               "armourer's scrap": rel_path('armorer.png'),
                               'orb of augmentation': rel_path('augmentation.png'),
                               "glassblower's bauble": rel_path('bauble.png'),
                               'blessed orb': rel_path('blessed.png'),
                               'orb of chance': rel_path('chance.png'),
                               'chaos orb': rel_path('chaos.png'),
                               "cartographer's chisel": rel_path('chisel.png'),
                               'chromatic orb': rel_path('chromatic.png'),
                               'divine orb': rel_path('divine.png'),
                               'exalted orb': rel_path('exalt.png'),
                               'exalted shard': rel_path('exaltShard.png'),
                               'orb of fusing': rel_path('fusing.png'),
                               "gemcutter's prism": rel_path('gcp.png'),
                               "jeweller's orb": rel_path('jeweller.png'),
                               'mirror of kalandra': rel_path('mirror.png'),
                               'perandus coin': rel_path('perandusCoin.png'),
                               "master cartographer's sextant": rel_path('redSextant.png'),
                               'regal orb': rel_path('regal.png'),
                               'orb of regret': rel_path('regret.png'),
                               'orb of scouring': rel_path('scouring.png'),
                               'silver coin': rel_path('silverCoin.png'),
                               'orb of transmutation': rel_path('transmutation.png'),
                               'vaal orb': rel_path('vaal.png'),
                               "blacksmith's whetstone": rel_path('whetstone.png'),
                               "apprentice cartographer's sextant": rel_path('whiteSextant.png'),
                               "journeyman cartographer's sextant": rel_path('yellowSextant.png')}
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
        self.inventoryMarkerImage = rel_path('inventoryMarker.png')
        self.inventorySlotLocations = {}
        print('Finder bot initialized.')

    def populate_currency_locations(self):
        """Decodes the stored currency tab slot locations back into the dict for easier access.
           Must always be called after find currency slots has been used at least once."""

        with open('currencyStashLocations.json', 'r') as f:
            j = json.load(f, cls=PointDecoder)
            for slot in j:
                self.currencyLocations[slot] = j[slot]

    def find_currency_slots(self, confidence=.95):
        """Should only be called when currency tab is completely empty (eg start of league/account).
           Runs perfectly when tested on 1920x1080 screen."""

        for img in self.currencyImages:
            p = Point(0, 0)
            # pyautogui has undocumented confidence parameter for locate function
            try:
                p.x, p.y = locateCenterOnScreen(self.currencyImages[img], confidence=confidence)
            except TypeError:
                print('Empty currency tab slot {0} not found.'.format(img))
            else:
                self.currencyLocations[img] = p
        with open('currencyStashLocations.json', 'w+') as f:
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

    def populate_inventory_slot_locations(self):
        """Decodes the stored inventory slot locations back into the dict for easier access.
           Must always be called after the find inventory slots method has been used at least once."""

        with open('inventorySlotLocations.json', 'r') as f:
            j = json.load(f, cls=PointDecoder)
            for slot in j:
                self.inventorySlotLocations[slot] = j[slot]

    def find_inventory_slots(self, confidence=.9):
        """Place ONE scroll of wisdom in the top left inventory slot (0) and call this function to get the coordinates.
           The corresponding image is 50x50 pixels on 1920x1080. After (0) is found the rest are calculated.
           Inventory chart:

                            0 5 10 15 20 25 30 35 40 45 50 55
                            1 6 11 16 21 26 31 36 41 46 51 56
                            2 7 12 17 22 27 32 37 42 47 52 57
                            3 8 13 18 23 28 33 38 43 48 53 58
                            4 9 14 19 24 29 34 39 44 49 54 59

           Should really only be called once at start of league or if your display settings change.
           The inventory should also be empty with the exception of the scroll of wisdom.
        """
        alert('Empty your inventory and place one scroll of wisdom in the top left slot.')
        sleep(1)
        loc = Point(0, 0)
        try:
            loc.x, loc.y = locateCenterOnScreen(self.inventoryMarkerImage, confidence=confidence)
        except TypeError:
            print('Inventory marker not found. Did you put a wisdom scroll in slot 0?')
        else:
            k = 0
            for x in range(12):
                for y in range(5):
                    self.inventorySlotLocations[k] = Point(loc.x + x * 52, loc.y + y * 52)
                    k += 1
            with open('inventorySlotLocations.json', 'w+') as f:
                json.dump(obj=self.inventorySlotLocations, fp=f,
                          cls=PointEncoder, indent=4, sort_keys=True)


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

        self.stashed_currency = {'scroll of wisdom': Currency(0, 0),
                                 'portal scroll': Currency(0, 0),
                                 'orb of alchemy': Currency(0, 0),
                                 'orb of alteration': Currency(0, 0),
                                 'orb of annulment': Currency(0, 0),
                                 "armourer's scrap": Currency(0, 0),
                                 'orb of augmentation': Currency(0, 0),
                                 "glassblower's bauble": Currency(0, 0),
                                 'blessed orb': Currency(0, 0),
                                 'orb of chance': Currency(0, 0),
                                 'chaos orb': Currency(0, 0),
                                 "cartographer's chisel": Currency(0, 0),
                                 'chromatic orb': Currency(0, 0),
                                 'divine orb': Currency(0, 0),
                                 'exalted orb': Currency(0, 0),
                                 'exalted shard': Currency(0, 0),
                                 'orb of fusing': Currency(0, 0),
                                 "gemcutter's prism": Currency(0, 0),
                                 "jeweller's orb": Currency(0, 0),
                                 'mirror of kalandra': Currency(0, 0),
                                 'perandus coin': Currency(0, 0),
                                 "master cartographer's sextant": Currency(0, 0),
                                 'regal orb': Currency(0, 0),
                                 'orb of regret': Currency(0, 0),
                                 'orb of scouring': Currency(0, 0),
                                 'silver coin': Currency(0, 0),
                                 'orb of transmutation': Currency(0, 0),
                                 'vaal orb': Currency(0, 0),
                                 "blacksmith's whetstone": Currency(0, 0),
                                 "apprentice cartographer's sextant": Currency(0, 0),
                                 "journeyman cartographer's sextant": Currency(0, 0)}

        inventory_level_update_thread = threading.Thread(target=self.continuous_inventory_level_update)
        inventory_level_update_thread.daemon = True
        inventory_level_update_thread.start()

        print('Inventory manager bot initialized.')

    def continuous_inventory_level_update(self):
        while True:
            self.check_stashed_currency()
            sleep(30)

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

    def item_in_stock(self, currency: str, amount: int) -> bool:
        return float(self.get_currency_count(currency)) >= float(amount)


class MessageParserBot:
    """Handles parsing of messages for the trade bot to use"""

    def __init__(self, interval=1):
        print('Initializing message parser bot...')
        self.interval = interval
        # holds the most recent message seen
        self.lastMessage = ''
        self.lastEnterMessage = ''
        self.lastZoneMessage = ''
        self.parsedMessage = {}
        thread1 = threading.Thread(target=self.monitor_client_text)
        thread1.daemon = True
        thread1.start()
        print('Message parser bot initialized.')

    tradeKey1 = "Hi, I'd like to buy your"
    tradeKey2 = "Hi, I would like to buy your"
    commandKey1 = "Execute66: "
    playerEnterKey = 'has joined the area'
    playerLeaveKey = 'has left the area'
    zoneChangeKey = 'You have entered'

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

    def check_last_line(self, file, tradeKey: str, tradeKey2: str,
                        commandKey1: str,
                        enterKey: str, leaveKey: str,
                        zoneKey: str):
        """searches the last line of the file for the search strings and sends it to the parser method"""

        for line in islice(self.reversed_lines(file), 1):
            s = line.rstrip('\n')
            if tradeKey in s or tradeKey2 in s:
                self.parse_trade_message(s)
            elif commandKey1 in s:
                self.parse_command_message(s)
            elif enterKey in s or leaveKey in s:
                self.parse_player_movement_message(s)
            elif zoneKey in s:
                self.parse_zone_change_message(s)

    def monitor_client_text(self):
        with open(CLIENTPATH, encoding="utf8") as clientFile:
            while True:
                # if the string is found parse it to extract necessary info
                self.check_last_line(file=clientFile,
                                     tradeKey=self.tradeKey1, tradeKey2=self.tradeKey2,
                                     commandKey1=self.commandKey1,
                                     enterKey=self.playerEnterKey, leaveKey=self.playerLeaveKey,
                                     zoneKey=self.zoneChangeKey)

                sleep(self.interval)

    def new_line(self, message: str) -> bool:
        """Handles making sure we don't needlessly send the same message to the central control"""

        return message != self.lastMessage

    def new_enter(self, enterMessage: str) -> bool:
        """Handles making sure we don't tell the CentralControl about a player entering that has already entered."""

        return enterMessage != self.lastEnterMessage

    def new_zone(self, enterMessage: str) -> bool:
        """Handles zone changes to ensure the list of players in current area is always correct."""

        return enterMessage != self.lastZoneMessage

    # TODO: Refactor this method
    # noinspection PyTypeChecker
    def parse_command_message(self, message: str):
        """Handles incoming commands sent through the game"""

        m = message.split('@')[1].split(' ')

        if self.new_line(m):
            if 'from' in m[0].lower():
                # incoming command found determine what it is and send the appropriate message
                for x in range(len(m)):
                    if self.commandKey1 in m[x]:
                        Event('new command', m[x + 1])

    def parse_zone_change_message(self, message: str):
        """Handles parsing zone change messages and notifying CentralControl of changes in zone."""

        if self.new_zone(message):
            self.lastZoneMessage = message

            Event('zone changed', None)

    def parse_player_movement_message(self, message: str):
        """Handles notifying the central control of players entering/leaving the area.
           Broadcasts an event containing a the player's name in string form"""

        splitMessage = message.split(' : ')[1]
        playerName = splitMessage.split(' ')[0]
        if self.new_enter(message):
            self.lastEnterMessage = message

            if self.playerEnterKey in splitMessage:
                Event('player entered area', playerName)
            elif self.playerLeaveKey in splitMessage:
                Event('player left area', playerName)

    # noinspection PyTypeChecker
    def parse_trade_message(self, message: str):
        """
        First, determines whether a trade is actually incoming by splitting and looking for "From"
        If the trade is determined to be incoming then extracts:
                -the person making the offer
                -what they want
                -their offer
                -the league they are in
        that info is sent to the central control in the form of a dict:
                {playerName, itemName, itemQuant, offerName, offerQuant, league}
        """

        playerName = None
        itemName = None
        itemQuant = None
        offerName = None
        offerQuant = None
        leagueName = None

        splitMessage = message.split('@')[1]
        # check to be sure we haven't already seen this line and detect if trade incoming
        if self.new_line(message) and 'from' in splitMessage.split(' ')[0].lower():
            self.lastMessage = message

            try:
                playerNameMessage = splitMessage.split(' ')
                if '<' in playerNameMessage[1] and '>' in playerNameMessage[1]:
                    playerName = playerNameMessage[2]
                else:
                    playerName = playerNameMessage[1]

                splitMessage = splitMessage.split('your ')[1].lower()

                itemMessage = splitMessage.split('my ')[0]
                for c in POETRADENAMES:
                    if c in itemMessage:
                        itemName = POETRADENAMES[c]
                        itemQuant = itemMessage.split(' ')[0]

                offerMessage = splitMessage.split('my ')[1]
                for c in POETRADENAMES:
                    if c in offerMessage:
                        offerName = POETRADENAMES[c]
                        offerQuant = offerMessage.split(' ')[0]

                for i in range(len(offerMessage.split(' '))):
                    if offerMessage.split(' ')[i] == 'in':
                        leagueName = offerMessage.split(' ')[i + 1]

                self.parsedMessage = {'playerName': playerName.strip(':'),
                                      'itemName': itemName, 'itemQuant': itemQuant,
                                      'offerName': offerName, 'offerQuant': offerQuant,
                                      'league': leagueName}

                for x in self.parsedMessage:
                    if self.parsedMessage[x] is None:
                        print("{0} failed to populate...".format(x))
                Event('new message', self.parsedMessage)
            except IndexError:
                print('Message not in Poe.trade form.')
