#!/usr/bin/env python3
LICENSE = '''\
Copyright (c) 2023 Theodore Kotz <ted@kotz.us>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.'''

import argparse
import serial
import threading
import sys
import time


def ConvertBytes2String(mybytes):
    return mybytes.decode()

def ConvertString2Bytes(mystring):
    return mystring.encode()

class HexTerm:

    def __init__(self, args: dict):
        self.args = args
        self.running = False

    def Char2BytesLoop(self):
        # print("entering C2B")
        while self.running:
            #time.sleep(1)
            line = self.readline()
            if line[0].upper() == "Q":
                self.running=False
            else:
                self.writeByte(ConvertString2Bytes(line))

    def Bytes2CharLoop(self):
        # print("entering B2C")
        count=0
        while self.running:
            #time.sleep(1)
            newByte = self.readByte()
            if (newByte is None) or (newByte == b""):
                pass
            elif count < 16:
                self.output(ConvertBytes2String(newByte)+" ")
                self.outputFlush()
                count += 1
            else:
                self.output(ConvertBytes2String(newByte)+"\n")
                count=0

    def mainloop(self) -> int:
        # print("entering main loop")
        b2c = threading.Thread(target=self.Bytes2CharLoop)
        c2b = threading.Thread(target=self.Char2BytesLoop)

        # Start both loops.
        b2c.start()
        c2b.start()

        # wait for join.
        b2c.join()
        self.running = False
        c2b.join()
        self.running = False

        print("Exiting")
        return 0


    def createOutput(self) -> int:
        self.output = sys.stdout.write
        self.outputFlush = sys.stdout.flush
        return self.mainloop()

    def createInput(self) -> int:
        self.readline = sys.stdin.readline
        return self.createOutput()

    def run(self) -> int:
        self.running = True
        print(self.args)

        # create Serial Device
        with serial.Serial(self.args.portname, self.args.baud, timeout=1) as port:
            self.readByte=lambda : port.read(1)
            self.writeByte=lambda b : port.write(b); port.flush()
            return self.createInput()

        self.running = False
        return -1


def main() -> int:
    global LICENSE
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    description = "Raw hexadecimal based terminal emulator for monitoring binary serial interfaces",
                    epilog = LICENSE)

    parser.add_argument('portname',                            metavar='PORT',                                help='uses named PORT')
    parser.add_argument('-b','--baud','--speed',               metavar='BAUDRATE',  type=int, default=9600,   help='sets the ports BUADRATE, default 9600')
    parser.add_argument('-f','--framing',                      metavar='8N1',                 default="8N1",  help='sets framing parameters in <DATABITS><PARITY><STOPBITS> form, default 8N1')
    parser.add_argument('-c','--flow-control','--control',     metavar='METHOD',              default="None", help='sets flow control METHOD [HW:(RTS/CTS), SW:(XON/XOFF), None:(default)]')

    args = parser.parse_args()

    hexterm = HexTerm( args )

    return hexterm.run()



if __name__ == '__main__':
    sys.exit(main())
