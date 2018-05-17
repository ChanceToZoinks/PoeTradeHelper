from PoEApiTools import PoeApiTools as pat
from itertools import islice
import os
import threading
import time


class CentralControl:
    """This is the central event handler. It holds the references for each of the three bots and contains callbacks
    necessary to maintain the correct order of events and to ensure trades are being completed."""


class TradeBot:
    """Handles collecting the currency and trading the correct person"""


class CurrencyFinderBot:
    """Handles locating the on screen coordinates of the currency in the currency tab for the trade bot"""


class MessageParserBot:
    """Handles parsing of messages for the trade bot to use"""
    def __init__(self, interval=1):
        self.interval = interval
        # this serves as a queue of sorts for trades
        self.messageList = []
        thread1 = threading.Thread(target=self.monitor_client_text)
        thread1.daemon = True
        thread1.start()

    clientPath = "C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt"
    testingPath = "C:\\Users\\Gabriel Akers\\Documents\\testing.txt"
    searchKey = "Hi, I'd like to buy your"

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

    def check_last_line(self, file, key):
        """searching the last line of the file for the info needed"""

        for line in islice(self.reversed_lines(file), 1):
            # if the string we need is found check against a list of messages and if not already contained add it
            s = line.rstrip('\n')
            if key in s:
                if s not in self.messageList:
                    self.messageList.append(s)
                    self.parse_trade_message(s)

    def monitor_client_text(self):
        while True:
            clientFile = open(self.testingPath)
            # if the string is found parse it to extract necessary info
            self.check_last_line(file=clientFile, key=self.searchKey)

            time.sleep(self.interval)

    def parse_trade_message(self, message):
        """Extracts:
                -the person making the offer
                -what they want
                -their offer
                -the league they are in
           that info is sent to the central control which is responsible for removing trades from the list"""
        print(message)
        print(self.messageList)

