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

DESCRIPTION = "Raw hexadecimal based terminal emulator for monitoring binary serial interfaces"

import argparse
import serial
import sys
import threading
import time


def makeprintable( s: str ) -> str:
    if (s.isprintable()):
        return s
    else:
        return "."

def format8bytes( b : bytes ) -> str:
    return b.hex(sep=' ').upper().ljust(24)


class HexTerm:

    def __init__(self, args: dict):
        self.args = args
        self.running = False

    def ConvertBytes2String(self, mybytes: bytes) -> str:
        return format8bytes(mybytes[0:8]) + " " + format8bytes(mybytes[8:16]) + " |" +"".join(map( makeprintable, mybytes.decode(encoding=self.args.encoding,errors='replace'))).ljust(16)+"|"

    def ConvertString2Bytes(self, mystring: str) -> bytes:
        try:
            if (mystring[0] == "'"):
                return mystring.split(sep="'")[1].encode(encoding=self.args.encoding)
            elif (mystring[0] == '"'):
                return mystring.split(sep='"')[1].encode(encoding=self.args.encoding)
            else:
                return bytes.fromhex(mystring)
        except Exception as e:
            print (e)
        return b""

    def Char2BytesLoop(self):
        # print("entering C2B")
        while self.running:
            #time.sleep(1)
            line = self.readline()
            if line[0].upper() == "Q":
                self.running=False
            else:
                self.writeByte(self.ConvertString2Bytes(line))

    def Bytes2CharLoop(self):
        # print("entering B2C")
        timestamp = time.time()
        data = bytearray()
        while self.running:
            #time.sleep(1)
            newByte = self.readByte()
            currTime = time.time()
            if (newByte is None) or (newByte == b""):
                pass
            else:
                if len(data) == 0:
                    timestamp = currTime
                data = data + newByte
            if (len(data) > 16) or ((len(data) > 0) and (currTime - timestamp) > 1):
                self.output("  "+self.ConvertBytes2String(data[0:16])+"\n")
                data = data[16:]
                timestamp = currTime

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
        with serial.Serial(self.args.portname, self.args.baud, timeout=320/self.args.baud) as port:
            self.readByte=lambda : port.read(16)
            self.writeByte=lambda b : port.write(b); port.flush()
            return self.createInput()

        self.running = False
        return -1


def main() -> int:
    global LICENSE
    global DESCRIPTION
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    description = DESCRIPTION,
                    epilog = LICENSE)

    parser.add_argument('portname',                            metavar='PORT',                                 help='uses named PORT')
    parser.add_argument('-b','--baud','--speed',               metavar='BAUDRATE',  type=int, default=9600,    help='sets the ports BUADRATE, default 9600')
    parser.add_argument('-c','--flow-control','--control',     metavar='METHOD',              default="None",  help='sets flow control METHOD [HW:(RTS/CTS), SW:(XON/XOFF), None:(default)]')
    parser.add_argument('-e','--encoding',                     metavar='CODEC',               default="cp437", help='sets encoding CODEC(ascii, latin-1, utf-8, etc), default cp437')
    parser.add_argument('-f','--framing',                      metavar='8N1',                 default="8N1",   help='sets framing parameters in <DATABITS><PARITY><STOPBITS> form, default 8N1')

    args = parser.parse_args()

    hexterm = HexTerm( args )

    return hexterm.run()



if __name__ == '__main__':
    sys.exit(main())
