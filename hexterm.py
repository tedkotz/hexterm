#!/usr/bin/env python3
'''
Raw hexadecimal based terminal emulator for monitoring binary serial interfaces

Copyright (c) 2023 Theodore Kotz <ted@kotz.us>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
'''

import argparse
import re
import sys
import threading
import time

import serial

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

def make_printable( txt : str, subst: str ="." ) -> str:
    """
    Returns `txt` with all the non printable characters replaced with `subst`,
    if not specified `subst` is "."
    """
    return "".join([ char if char.isprintable() else subst for char in txt])

def format8bytes( arr : bytes ) -> str:
    """
    Formats 8 bytes into a string of hex digits
    """
    return arr.hex(sep=' ').upper().ljust(24)


BYTESIZES = {
    "5": serial.FIVEBITS,
    "6": serial.SIXBITS,
    "7": serial.SEVENBITS,
    "8": serial.EIGHTBITS
}
def determine_serial_byte_size( arg : str )-> 'serial.ByteSize':
    """
    Converts command line bits per byte are to a serial BITS configuration
    """
    return BYTESIZES.get(arg, serial.EIGHTBITS)

PARITIES = {
    "N":serial.PARITY_NONE,
    "E":serial.PARITY_EVEN,
    "O":serial.PARITY_ODD,
    "M":serial.PARITY_MARK,
    "S":serial.PARITY_SPACE
}
def determine_serial_parity( arg: str ) -> 'serial.Parity':
    """
    Converts command line serial parity bit type to a serial Parity configuration
    """
    return PARITIES.get(arg, serial.PARITY_NONE)

STOPBITS = {
    "1":serial.STOPBITS_ONE,
    "1.5":serial.STOPBITS_ONE_POINT_FIVE,
    "2":serial.STOPBITS_TWO
}
def determine_serial_stop_bits( arg: str ) -> 'serial.StopBits':
    """
    Converts command line number of stop bits to a serial Stop Bits configuration
    """
    return STOPBITS.get(arg, serial.STOPBITS_ONE)

def parse_serial_framing( settings: str
    ) -> ['serial.ByteSize', 'serial.Parity', 'serial.StopBits']:
    """
    Converts "8N1" format serial framing description into serial configuration
    parameters
    """
    match = re.fullmatch(r"^([5-8]?)([EMNOS]?)((1\.5)|2|1?)$", settings.strip().upper())
    if match is None:
        raise ValueError( f"framing settings parse error in '{settings}'" )
    byte_size = determine_serial_byte_size(match.group(1))
    parity = determine_serial_parity(match.group(2))
    stop_bits = determine_serial_stop_bits(match.group(3))
    return byte_size, parity, stop_bits



FLOWCONTROLSETTINGS = {
    "NONE":  ( False, False, False ),
    "SW":    ( True,  False, False ),
    "HW":    ( False, True,  False ),
    "RTS":   ( False, True,  False ),
    "DSR":   ( False, False, True  ),
    "ALL":   ( True,  True,  True  ),
}
def parse_serial_flow_control( arg: str
    ) -> [bool('xonxoff'), bool('rtscts'), bool('dsrdtr')]:
    """
    Converts Flow control specification description into serial configuration
    parameters
    """
    flow_control = FLOWCONTROLSETTINGS.get(arg.upper())
    if flow_control is None:
        raise ValueError( f"flow control settings parse error in '{arg}'" )
    return flow_control[0], flow_control[1], flow_control[2]

class HexTerm:
    """
    Hexterminal main threads and routing.
    """

    def __init__(self, args: 'argparse.Namespace'):
        self.args = args
        self.shutdown = threading.Event()
        self.output = None
        self.output_flush = None
        self.readline = None
        self.read_byte = None
        self.write_byte = None

    def convert_16bytes_to_string(self, mybytes: bytes) -> str:
        """
        Converts 16 bytes to a printable line of text
        """
        decoded_bytes = mybytes.decode(encoding=self.args.encoding,errors='replace')
        return_val  = format8bytes(mybytes[0:8]) + " " + format8bytes(mybytes[8:16]) + " |"
        return_val += make_printable(decoded_bytes).ljust(16)+"|"
        return return_val

    def _extract_bytes(self, txt: str ) -> bytes:
        if not isinstance(txt, str):
            return b""
        txt = txt.lstrip()
        if txt == "":
            return b""

        if txt[0] in "0123456789abcdefABCDEF":
            return bytes.fromhex(txt[0:2]) + self._extract_bytes(txt[2:])
        if "'"==txt[0]:
            mylist = txt.split(sep="'", maxsplit=3) + [""]
            return mylist[1].encode(encoding=self.args.encoding) + self._extract_bytes(mylist[2])
        if '"'==txt[0]:
            mylist = txt.split(sep='"', maxsplit=3) + [""]
            return mylist[1].encode(encoding=self.args.encoding) + self._extract_bytes(mylist[2])
        raise ValueError("does not match hexterm command")

    def convert_string_to_bytes(self, txt: str) -> bytes:
        """
        Convert user input string to raw bytes for sending over the wire
        """
        try:
            return self._extract_bytes(txt)
        except UnicodeEncodeError as exception: # encode()
            print (f"UnicodeEncodeError({exception}) in '{txt}'")
        except ValueError as exception: # fromhex() and fall-through _extract_bytes case
            print (f"ValueError({exception}) in '{txt}'")
        return b""

    def local_input_loop(self):
        """
        Processing loop for the data coming in locally
        """
        while not self.shutdown.is_set():
            #time.sleep(1)
            line = self.readline()
            # EOF or quit
            if line == "" or line[0].upper() == "Q":
                self.shutdown.set()
            else:
                self.write_byte(self.convert_string_to_bytes(line))

    def serial_input_loop(self):
        """
        Processing loop for the data coming in the serial port
        """
        timestamp = time.time()
        data = bytearray()
        while not self.shutdown.is_set():
            #time.sleep(1)
            new_byte = self.read_byte()
            curr_time = time.time()
            if (new_byte is None) or (new_byte == b""):
                pass
            else:
                if len(data) == 0:
                    timestamp = curr_time
                data = data + new_byte
            if (len(data) > 16) or ((len(data) > 0) and (curr_time - timestamp) > 1):
                self.output("  "+self.convert_16bytes_to_string(data[0:16])+"\n")
                data = data[16:]
                timestamp = curr_time

    def mainloop(self) -> int:
        """
        Main processing control loop
        """
        b2c = threading.Thread(target=self.serial_input_loop)
        c2b = threading.Thread(target=self.local_input_loop)

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


    def create_local_output_stream(self) -> int:
        """
        Parses the output settings and then passes control
        """
        if self.args.output == "-":
            self.output = sys.stdout.write
            self.output_flush = sys.stdout.flush
            return self.mainloop()
        # else
        with open(self.args.output, "a+", encoding="utf-8") as outfile:
            self.output = outfile.write
            self.output_flush = outfile.flush
            return self.mainloop()

    def create_local_input_stream(self) -> int:
        """
        Parses the input settings and then passes control
        """
        if self.args.input == "-":
            self.readline = sys.stdin.readline
            return self.create_local_output_stream()
        # else
        with open(self.args.input, "r", encoding="utf-8") as infile:
            self.readline = infile.readline
            return self.create_local_output_stream()


    def run(self) -> int:
        """
        Entry point for passing control to the Hexterm
        """
        self.shutdown.clear()
        print(str(self.args).replace("Namespace","Settings",1))
        print("Type 'quit' to exit")

        # create Serial Device

        bytesize, parity, stopbits = parse_serial_framing(self.args.framing)
        xonxoff, rtscts, dsrdtr = parse_serial_flow_control(self.args.flow_control)

        with serial.Serial(port=self.args.portname, baudrate=self.args.baud, bytesize=bytesize,
        parity=parity, stopbits=stopbits, xonxoff=xonxoff, rtscts=rtscts, dsrdtr=dsrdtr,
        timeout=320/self.args.baud) as port:
            def read_port():
                return port.read(16)
            self.read_byte=read_port

            def write_port( mybytes ):
                port.write(mybytes)
                port.flush()
            self.write_byte=write_port

            return self.create_local_input_stream()

        self.shutdown.set()
        return -1


def main() -> int:
    """
    Global main for hexterm
    """
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
