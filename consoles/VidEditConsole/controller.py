from future_client import FutureClient, Game, MessageSlot
import serial
import serial.tools.list_ports as list_ports
import time
import struct
import threading
import random

illum_count = 25
led_count = 12

class Controller:
    def __init__(self):
        ports={}
        for (name,_,_) in list_ports.grep('/dev/ttyACM*'):
            port = serial.Serial(name, timeout=3)
            port.write('I\n')
            teensyid = port.readline().strip()
            ports[teensyid] = port
        for (i,p) in ports.items():
            print("Found {0}".format(i))
        self.t=ports['teensy']
        self.tpp=ports['teensypp']
        # imap entries are (pressed, mode)
        self.imap = [(False,0)]*illum_count
        self.t.write('m\\x0cmBoot sequence\\ncomplete.\n')
        time.sleep(0.5)
        self.t.write('m\\x0c\n')
        for i in range(illum_count):
            self.set_illuminated(i,0)
        
    def get_keypresses(self):
        ipressed = []
        self.tpp.write('r\n')
        keys = self.tpp.readline().strip()
        for i in range(illum_count):
            newp = keys[i]=='1'
            (oldp,mode) = self.imap[i]
            if (newp and not oldp):
                # button down press
                ipressed.append(i)
            self.imap[i] = (newp,mode)
        return ipressed
    def set_illuminated(self,i,mode):
        self.t.write('i{0}:{1}\n'.format(i,mode))
        (oldp, _) = self.imap[i]
        self.imap[i] = (oldp, mode)
    def set_led(self,i,mode):
        self.t.write('l{0}:{1}\n'.format(i,mode))
    def send_msg(self,msg,clear=True):
        if msg == None:
            msg = ''
        if clear:
            msg = '\x0c'+msg
        msg = msg.replace('\n','\\n')
        self.t.write('m{0}\n'.format(msg))



class PressBlinkersGame(Game):
    def __init__(self,c):
        super(PressBlinkersGame, self).__init__('blinkers','Disable blinking buttons')
        self.c = c
        self.candidates = set(range(illum_count))
        self.candidates.remove(11) # #11 doesn't illuminate :(

    def make_blinkers(self):
        count = random.randint(4,10)
        self.blinkers=set(random.sample(self.candidates,count))

    def play_game(self):
        self.make_blinkers()
        for i in range(illum_count):
            if i in self.blinkers:
                c.set_illuminated(i,4)
            else:
                c.set_illuminated(i,0)
        starttime = time.time()
        while self.running and (time.time()-starttime) < 10.0:
            time.sleep(0.05)
            for i in c.get_keypresses():
                if i in self.blinkers:
                    c.set_illuminated(i,0)
                    self.blinkers.remove(i)
            if len(self.blinkers) == 0:
                self.finish(True,5)
                return
        if self.running:
            self.finish(False,-5);

    def on_start(self):
        t = threading.Thread(target = self.play_game)
        self.thread = t
        t.start()

class SyncBlinkersGame(Game):
    def __init__(self,c):
        super(SyncBlinkersGame, self).__init__('synchronize','Synchronize blinking buttons')
        self.c = c
        self.candidates = set(range(illum_count))
        self.candidates.remove(11) # #11 doesn't illuminate :(

    def make_blinkers(self):
        count = random.randint(6,14)
        part = count/2
        self.a=set(random.sample(self.candidates,count))
        self.b=set(random.sample(self.a,part))
        self.a=self.a.difference(self.b)

    def play_game(self):
        self.make_blinkers()
        for i in range(illum_count):
            if i in self.a:
                c.set_illuminated(i,2)
            elif i in self.b:
                c.set_illuminated(i,3)
            else:
                c.set_illuminated(i,0)
        starttime = time.time()
        while self.running and (time.time()-starttime) < 15.0:
            time.sleep(0.05)
            for i in c.get_keypresses():
                if i in self.a:
                    c.set_illuminated(i,3)
                    self.a.remove(i)
                    self.b.add(i)
                elif i in self.b:
                    c.set_illuminated(i,2)
                    self.b.remove(i)
                    self.a.add(i)
            if (len(self.a) == 0) or (len(self.b) == 0):
                self.finish(True,5)
                return
        if self.running:
            self.finish(False,-5);

    def on_start(self):
        t = threading.Thread(target = self.play_game)
        self.thread = t
        t.start()

class LCDSlot(MessageSlot):
    def __init__(self, c, id=None, length=40):
        self.c = c
        super(LCDSlot, self).__init__(id,length)

    def on_message(self,text):
        self.c.send_msg(text)

c = Controller()

games = [
    PressBlinkersGame(c),
    SyncBlinkersGame(c)
]

slots = [
    LCDSlot(c),
]

import sys

if __name__ == '__main__' and len(sys.argv) == 1:
    fc = FutureClient('ws://localhost:8888/socket','VidEditConsole')
    fc.available_games = games
    fc.message_slots = slots
    fc.start()
    while True:
        try:
            time.sleep(0.05)
        except:
            fc.quit()
            break
else:
    # test mode
    for i in range(led_count):
        c.set_led(i,1)
        time.sleep(0.5)
        c.set_led(i,0)
    for i in range(illum_count):
        c.set_illuminated(i,1)
        time.sleep(0.5)
        c.set_illuminated(i,0)
    while True:
        for i in c.get_keypresses():
            print i
