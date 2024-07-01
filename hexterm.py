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
import re
import sys
import threading
import time

import serial

def makeprintable( s: str ) -> str:
    if s.isprintable():
        return s
    else:
        return "."

def format8bytes( b : bytes ) -> str:
    """
    Formats 8 bytes into a string of hex digits
    """
    return b.hex(sep=' ').upper().ljust(24)


def determineSerialByteSize( bs: str )-> 'serial.ByteSize':
    """
    Converts command line bits per byte are to a serial BITS configuration
    """
    ByteSizes = {
        "5": serial.FIVEBITS,
        "6": serial.SIXBITS,
        "7": serial.SEVENBITS,
        "8": serial.EIGHTBITS
    }
    return ByteSizes.get(bs, serial.EIGHTBITS)

def determineSerialParity( p: str ) -> 'serial.Parity':
    """
    Converts command line serial parity bit type to a serial BITS configuration
    """
    Parities = {
        "N":serial.PARITY_NONE,
        "E":serial.PARITY_EVEN,
        "O":serial.PARITY_ODD,
        "M":serial.PARITY_MARK,
        "S":serial.PARITY_SPACE
    }
    return Parities.get(p, serial.PARITY_NONE)

def determineSerialStopBits( sb: str ) -> 'serial.StopBits':
    """
    Converts command line number of stop bits to a serial BITS configuration
    """
    StopBits = {
        "1":serial.STOPBITS_ONE,
        "1.5":serial.STOPBITS_ONE_POINT_FIVE,
        "2":serial.STOPBITS_TWO
    }
    return StopBits.get(sb, serial.STOPBITS_ONE)

def parseSerialFraming( settings: str) -> ['serial.ByteSize', 'serial.Parity', 'serial.StopBits']:
    match = re.fullmatch(r"^([5-8]?)([EMNOS]?)((1\.5)|2|1?)$", settings.strip().upper())
    if match is None:
        raise Exception( "Framing settings parse error in '{}'.".format( settings ) )
    bs = determineSerialByteSize(match.group(1))
    p = determineSerialParity(match.group(2))
    sb = determineSerialStopBits(match.group(3))
    return bs, p, sb


def parseSerialFlowControl( flowControl: str ) -> [bool('xonxoff'), bool('rtscts'), bool('dsrdtr')]:
    s = flowControl.upper()
    if s == "NONE":
        return False, False, False
    elif s == "SW":
        return True, False, False
    elif s == "HW" or s == "RTS":
        return False, True, False
    elif s == "DSR":
        return False, False, True
    elif s == "ALL":
        return True, True, True
    raise Exception( "Flow Control settings parse error in '{}'.".format( flowControl ) )

class HexTerm:

    def __init__(self, args: 'argparse.Namespace'):
        self.args = args
        self.shutdown = threading.Event()
        self.output = None
        self.outputFlush = None
        self.readline = None
        self.readByte = None
        self.writeByte = None

    def ConvertBytes2String(self, mybytes: bytes) -> str:
        decoded_bytes = mybytes.decode(encoding=self.args.encoding,errors='replace')
        return_val  = format8bytes(mybytes[0:8]) + " " + format8bytes(mybytes[8:16]) + " |"
        return_val += "".join(map( makeprintable, decoded_bytes)).ljust(16)+"|"
        return return_val

    def parseBytes(self, s: str ) -> bytes:
        if not isinstance(s, str):
            return b""
        s = s.lstrip()
        if s == "":
            return b""

        if s[0] in "0123456789abcdefABCDEF":
            return bytes.fromhex(s[0:2]) + self.parseBytes(s[2:])
        elif "'"==s[0]:
            l = s.split(sep="'", maxsplit=3) + [""]
            return l[1].encode(encoding=self.args.encoding) + self.parseBytes(l[2])
        elif '"'==s[0]:
            l = s.split(sep='"', maxsplit=3) + [""]
            return l[1].encode(encoding=self.args.encoding) + self.parseBytes(l[2])
        else:
            raise Exception("Syntax Error")

    def ConvertString2Bytes(self, mystring: str) -> bytes:
        try:
            return self.parseBytes(mystring)
        except Exception as e:
            print (e)
        return b""

    def Char2BytesLoop(self):
        while not self.shutdown.is_set():
            #time.sleep(1)
            line = self.readline()
            # EOF or quit
            if line == "" or line[0].upper() == "Q":
                self.shutdown.set()
            else:
                self.writeByte(self.ConvertString2Bytes(line))

    def Bytes2CharLoop(self):
        timestamp = time.time()
        data = bytearray()
        while not self.shutdown.is_set():
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
        b2c = threading.Thread(target=self.Bytes2CharLoop)
        c2b = threading.Thread(target=self.Char2BytesLoop)

        # Start both loops.
        b2c.start()
        c2b.start()

        # wait for join.
        b2c.join()
        self.shutdown.set()
        c2b.join()
        self.shutdown.set()

        print("Exiting")
        return 0


    def createOutput(self) -> int:
        if self.args.output == "-":
            self.output = sys.stdout.write
            self.outputFlush = sys.stdout.flush
            return self.mainloop()
        # else
        with open(self.args.output, "a+") as outfile:
            self.output = outfile.write
            self.outputFlush = outfile.flush
            return self.mainloop()

    def createInput(self) -> int:
        if self.args.input == "-":
            self.readline = sys.stdin.readline
            return self.createOutput()
        # else
        with open(self.args.input, "r") as infile:
            self.readline = infile.readline
            return self.createOutput()


    def run(self) -> int:
        self.shutdown.clear()
        print(str(self.args).replace("Namespace","Settings",1))
        print("Type 'quit' to exit")

        # create Serial Device

        bytesize, parity, stopbits = parseSerialFraming(self.args.framing)
        xonxoff, rtscts, dsrdtr = parseSerialFlowControl(self.args.flow_control)

        with serial.Serial(port=self.args.portname, baudrate=self.args.baud, bytesize=bytesize,
        parity=parity, stopbits=stopbits, xonxoff=xonxoff, rtscts=rtscts, dsrdtr=dsrdtr,
        timeout=320/self.args.baud) as port:
            self.readByte=lambda : port.read(16)
            self.writeByte=lambda b : port.write(b); port.flush()
            return self.createInput()

        self.shutdown.set()
        return -1


def main() -> int:
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    description = DESCRIPTION,
                    epilog = LICENSE)

    parser.add_argument('portname',
        metavar='PORT',
        help='uses named PORT')
    parser.add_argument('-b','--baud','--speed',
        metavar='BAUDRATE',  type=int, default=9600,
        help='sets the ports BUADRATE, default 9600')
    parser.add_argument('-c','--flow-control','--control',
        metavar='METHOD',              default="None",
        help='sets flow control METHOD [HW:(RTS/CTS), SW:(XON/XOFF), None:(default)]')
    parser.add_argument('-e','--encoding',
        metavar='CODEC',               default="cp437",
        help='sets encoding CODEC(ascii, latin-1, utf-8, etc), default cp437')
    parser.add_argument('-f','--framing',
        metavar='8N1',                 default="8N1",
        help='sets framing in <DATABITS[5-8]><PARITY[EMNOS]><STOPBITS[1,1.5,2]> form, default 8N1')
    parser.add_argument('-i','--input',
        metavar='FILENAME',            default="-",
        help='input is read from FILENAME')
    parser.add_argument('-o','--output',
        metavar='FILENAME',            default="-",
        help='output is appended to FILENAME')

    args = parser.parse_args()

    hexterm = HexTerm( args )

    return hexterm.run()


if __name__ == '__main__':
    sys.exit(main())
