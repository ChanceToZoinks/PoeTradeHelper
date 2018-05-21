from itertools import islice
import os
import threading
from time import sleep
from pyautogui import *
from Observable import *
from PoEApiTools import *
import ctypes
import ctypes.wintypes
from subprocess import run

FAILSAFE = True
POEPATH = "C:\Program Files (x86)\Grinding Gear Games\Path of Exile\PathOfExile.exe"


class Point:
    """2D point in space data structure."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


class CentralControl(Observer):
    """This is the central event handler. It holds the references for each of the five bots and contains callbacks
    necessary to maintain the correct order of events and to ensure trades are being completed.
    Holds instances of the three bot types"""

    def __init__(self, league='Bestiary', interval=1):
        # Observer's init needs to be called
        Observer.__init__(self)

        self.interval = interval
        self.parser = MessageParserBot()
        self.finder = ItemFinderBot()
        self.trader = TradeBot()
        self.messenger = MessengerBot()
        self.inventory = InventoryManagerBot()

        # opens poe and gets the hwnd and makes poe foreground/active window
        try:
            run(POEPATH)
        except FileNotFoundError:
            print("Can't find PoE executable. Check your POEPATH.")
        win = getWindow("Path of Exile")
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

    def transact_trade(self, tradeData):
        """Handles the trading by calling the appropriate methods in the bots"""

        # first check to be sure we even have the item

        # if we dont have the item inform the player otherwise invite them

        # click the correct screen locations to complete the trade

    def new_trade_message_received(self, messageData):
        """Callback for trade message being received. Appends the trade to the list if the ratio offered is correct."""

        print(messageData)
        if self.ratio_checker(itemName=messageData['itemName'],
                              itemQuant=messageData['itemQuant'],
                              offer=messageData['offerQuant']):
            # ratio matches so append to the trade queue and begin the the trade sequence
            self.tradeList.append(messageData)

    def new_command_message_received(self, command):
        """Callback for command received."""

        print(command)

    def ratio_checker(self, itemName, itemQuant, offer):
        """Checks the ratio of chaos offered/items requested to make sure they match the ratio we selling at"""

        return float(offer)/float(itemQuant) == self.sellRatios[itemName]


class TradeBot:
    """Handles collecting the currency and trading the correct person in addition to kicking, changing hideouts.
       Holds methods to perform chat console commands and click the mouse at the correct locations."""

    def __init__(self):
        print('Initializing trade bot...')
        print('Trade bot initialized.')

    def shift_click(self, point):
        """Ctrl+left clicks at a location. Point is of type Point."""

        keyDown('shift')
        click(x=point.x, y=point.y)
        keyUp('shift')

    def control_click(self, point):
        """Ctrl+left clicks at a location. Point is of type Point."""

        keyDown('ctrl')
        click(x=point.x, y=point.y)
        keyUp('ctrl')

    def invite_player(self, playerName):
        """Handles inviting the correct player to the group."""

        press('enter')
        typewrite('/invite {0}'.format(playerName))
        press('enter')

    def kick_player(self, playerName):
        """Handles kicking players."""

        press('enter')
        typewrite('/kick {0}'.format(playerName))
        press('enter')

    def init_trade(self, playerName):
        """Handles initiation of trade with a player. Returns true so it can be queued."""

        press('enter')
        typewrite('/tradewith {0}'.format(playerName))
        press('enter')

    def go_hideout(self, playerName):
        """Handles travelling to hideouts. Returns true so it can be queued."""

        press('enter')
        typewrite('/hideout {0}'.format(playerName))
        press('enter')


class ItemFinderBot:
    """Handles locating the on screen coordinates of the currency in the currency tab for the trade bot"""

    def __init__(self):
        print('Initializing item finder bot...')
        print('Item finder bot initialized.')


class MessengerBot:
    """Handles response to messages including commands sent to the central command"""

    def __init__(self):
        print('Initializing messenger bot...')

        print('Messenger bot initialized.')

    def build_message(self, target, messagestring):
        """Sets the class level variable 'msg' which can then be used."""

        return "@{0} {1}".format(target, messagestring)

    def send_message(self, message):
        """Handles messaging players."""

        press('enter')
        typewrite(message)
        press('enter')


class InventoryManagerBot:
    """Handles inventory management"""

    def __init__(self):
        print('Initializing inventory manager bot...')
        print('Inventory manager bot initialized.')


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

    clientPath = "C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt"
    testingPath = "C:\\Users\\Gabriel Akers\\Documents\\testing.txt"
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

    def check_last_line(self, file, key, key2, key3):
        """searches the last line of the file for the search strings and sends it to the parser method"""

        for line in islice(self.reversed_lines(file), 1):
            s = line.rstrip('\n')
            if key in s or key2 in s:
                self.parse_trade_message(s)
            elif key3 in s:
                self.parse_command_message(s)

    def monitor_client_text(self):
        with open(self.testingPath) as clientFile:
            while True:
                # if the string is found parse it to extract necessary info
                self.check_last_line(file=clientFile, key=self.tradeKey1, key2=self.tradeKey2, key3=self.commandKey1)

                sleep(self.interval)

    def new_line(self, message):
        """Handles making sure we don't needlessly send the same message to the central control"""

        if message == self.lastMessage:
            return False
        else:
            self.lastMessage = message
            return True

    def parse_command_message(self, message):
        """Handles incoming commands sent through the game"""

        m = message.split('@')[1].split(' ')

        if self.new_line(m):
            if 'from' in m[0].lower():
                # incoming command found determine what it is and send the appropriate message
                for x in range(len(m)):
                    if self.commandKey1 in m[x]:
                        Event('new command', m[x+1])

    def parse_trade_message(self, message):
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

        # check to be sure we haven't already seen this line
        if self.new_line(m):
            # detect if the trade is incoming
            if 'from' in m[0].lower():
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
