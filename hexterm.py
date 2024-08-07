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
import queue
import re
import sys
import threading
import time
import typing

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

START_TIME = time.time()

## Configuration parsing functions #############################################

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
    "CTS":   ( False, True,  False ),
    "DTR":   ( False, False, True  ),
    "DSR":   ( False, False, True  ),
    "SW/HW": ( True,  True,  False ),
    "SW/RTS":( True,  True,  False ),
    "SW/CTS":( True,  True,  False ),
    "SW/DSR":( True,  False, True  ),
    "SW/DTR":( True,  False, True  ),
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


## Input parsing functions #################################################

def convert_string_to_bytes(txt: str, encoding: str) -> bytes:
    """
    Convert user input string to raw bytes for sending over the wire
    """
    def _extract_bytes(txt: str) -> bytes:
        if not isinstance(txt, str):
            return b""
        txt = txt.lstrip()
        if txt == "":
            return b""

        if "'"==txt[0]:
            mylist = txt.split(sep="'", maxsplit=2) + [""]
            return mylist[1].encode(encoding=encoding) + _extract_bytes(mylist[2])
        if '"'==txt[0]:
            mylist = txt.split(sep='"', maxsplit=2) + [""]
            print(mylist)
            return mylist[1].encode(encoding=encoding) + _extract_bytes(mylist[2])
        # Must be hex digits
        mylist = txt.split(maxsplit=1)+[""]
        txt=mylist[0]
        if len(txt) % 2 == 1:
            txt = "0"+txt
        return bytes.fromhex(txt) + _extract_bytes(mylist[1])

    try:
        return _extract_bytes(txt)
    except UnicodeEncodeError as exception: # encode()
        print (f"UnicodeEncodeError({exception}) in '{txt.strip()}'")
    except ValueError as exception: # fromhex() and fall-through _extract_bytes case
        print (f"ValueError({exception}) in '{txt.strip()}'")
    return b""


## Output formatting functions #################################################

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

def convert_16bytes_to_string(mybytes: bytes, encoding: str) -> str:
    """
    Converts 16 bytes to a printable line of text
    """
    decoded_bytes = mybytes.decode(encoding=encoding, errors='replace')
    return_val  = format8bytes(mybytes[0:8]) + " " + format8bytes(mybytes[8:16]) + " |"
    return_val += make_printable(decoded_bytes).ljust(16)+"|"
    return return_val


class IO(typing.NamedTuple):
    """
    Tuple of the I/O functions expected by Hexterm
    """
    read: typing.Callable
    write: typing.Callable
    flush: typing.Callable

def _void( *_ ):
    return None

NullIO = IO(_void, _void, _void)

class DataRead(typing.NamedTuple):
    """
    Tuple of the fields from serial input loop to local output loop
    """
    timestamp: "Time"
    data: bytes



class HexTerm:
    """
    Hexterminal main threads and routing.
    """
    def __init__(self, args: 'argparse.Namespace'):
        self.args = args
        self.shutdown = threading.Event()
        self.local = None
        self.dce = None
        self.dce_print_queue = queue.Queue()
        self.dte = None
        self.dte_print_queue = queue.Queue()


    def local_input_loop(self):
        """
        Processing loop for the data coming in locally
        """
        while not self.shutdown.is_set():
            line = self.local.read()
            # EOF or quit
            if line == "" or line[0].upper() == "Q":
                self.shutdown.set()

            # Help
            elif line[0].upper() in "H?":
                print(" help    - Print commands")
                print(" quit    - Exit program")
                print(" wait X  - Wait for X seconds before continuing")
                print(' <HEX>   - Send message of raw hexadecimal bytes')
                print(' "text"  - Send message of decoded text string as bytes')
                print(" 'text'  - Send message of decoded text string as bytes")
                print(" t <msg> - In mitm mode, send msg to the 2nd mitm DTE port")

            # Wait
            elif line[0].upper() == "W":
                try:
                    secs = float(line.split()[1])
                except IndexError:
                    secs = 1
                except ValueError:
                    secs = 1
                except TypeError:
                    secs = 1
                time.sleep(secs)
                print("done.")

            # DTE Send
            elif line[0].upper() == "T":
                if self.dte is None:
                    print("DTE only supported in mitm monitor mode.")
                else:
                    self.dte.write(convert_string_to_bytes(line[1:], self.args.encoding))
                    self.dte.flush()

            # DCE Send
            else:
                self.dce.write(convert_string_to_bytes(line, self.args.encoding))
                self.dce.flush()



    def serial_output_loop(self, input_queue, prefix=""):
        """
        Processing loop for the data coming from the serial port to the local output
        """
        #msg_timeout = (MSG_BYTES * (STARTBIT+DATABITS+PARITY+STOPBITS))/self.args.baud
        msg_timeout = (16 * 12)/self.args.baud
        data = bytearray()
        entry = None
        if self.args.timestamp is None:
            print_timestamp = bool(self.args.mitm)
        else:
            print_timestamp = bool(self.args.timestamp)
        curr_time = time.time()
        start_timestamp = curr_time
        while True:
            try:
                timeout = None if len(data) < 1 else msg_timeout - (curr_time - start_timestamp)
                entry = input_queue.get(timeout=timeout)
                curr_time = entry.timestamp
                if bool(entry.data):
                    if len(data) < 1:
                        start_timestamp = curr_time
                    data = data + entry.data
            except queue.Empty :
                curr_time = time.time()
                entry = None
            if (len(data) >= 16) or ((len(data) > 0) and
                                     (curr_time - start_timestamp) > msg_timeout):
                txt=convert_16bytes_to_string(data[0:16], self.args.encoding)
                txt=f"{prefix}: {txt}\n"
                if print_timestamp:
                    txt=f"{{{(start_timestamp - START_TIME) :012.6f}}} {txt}"
                self.local.write(txt)
                data = data[16:]
                start_timestamp = curr_time
            if entry is not None:
                input_queue.task_done()

    def dce_output_loop(self):
        """
        Processing loop for the data coming from the DCE serial port to the local output
        """
        if self.args.mitm is not None:
            self.serial_output_loop( self.dce_print_queue, "T <- C" )
        else:
            self.serial_output_loop( self.dce_print_queue )

    def dte_output_loop(self):
        """
        Processing loop for the data coming from the DTE serial port to the local output
        """
        self.serial_output_loop( self.dte_print_queue, "T -> C" )

    def _forward_to_mitm(self):
        if self.args.mitm is None:
            if self.args.forward:
                raise RuntimeError('byte forwarding cannot be enabled outside of monitor mode.')
        elif self.args.forward is None or self.args.forward:
            return True
        return False

    def serial_input_loop(self, serial_read, serial_write, output_queue):
        """
        Processing loop for the data coming in the serial port
        """
        max_bytes_read_per_cycle = 16
        if serial_read:
            if self._forward_to_mitm() and serial_write:
                while not self.shutdown.is_set():
                    new_bytes = serial_read.read(max_bytes_read_per_cycle)
                    if new_bytes:
                        serial_write.write(new_bytes)
                        output_queue.put_nowait( DataRead(time.time(), new_bytes) )
            else:
                while not self.shutdown.is_set():
                    new_bytes = serial_read.read(max_bytes_read_per_cycle)
                    if new_bytes:
                        output_queue.put_nowait( DataRead(time.time(), new_bytes) )

    def dce_input_loop(self):
        """
        Processing loop for the data coming in the DCE serial port
        """
        self.serial_input_loop( self.dce, self.dte, self.dce_print_queue)
        print("Exiting DCE.")

    def dte_input_loop(self):
        """
        Processing loop for the data coming in the DTE serial port
        """
        self.serial_input_loop( self.dte, self.dce, self.dte_print_queue)
        print("Exiting DTE.")


    def mainloop(self) -> int:
        """
        Main processing control loop
        """
        dte_rx_thread = threading.Thread(target=self.dte_input_loop)
        dce_rx_thread = threading.Thread(target=self.dce_input_loop)
        dte_print_thread = threading.Thread(target=self.dte_output_loop, daemon=True)
        dce_print_thread = threading.Thread(target=self.dce_output_loop, daemon=True)

        # Start support threads
        dte_print_thread.start()
        dce_print_thread.start()
        dte_rx_thread.start()
        dce_rx_thread.start()

        # Start Local RX Thread
        self.local_input_loop()
        self.shutdown.set()
        print("Exiting.")

        # wait for join.
        dte_rx_thread.join()
        dce_rx_thread.join()

        self.dte_print_queue.join()
        self.dce_print_queue.join()

        return 0


    def create_local_output_stream(self, readline: typing.Callable) -> int:
        """
        Parses the output settings and then passes control
        """
        if self.args.output == "-":
            self.local = IO( readline, sys.stdout.write, sys.stdout.flush)
            return self.mainloop()
        # else
        with open(self.args.output, "a+", encoding="utf-8") as outfile:
            self.local = IO( readline, outfile.write, outfile.flush)
            return self.mainloop()

    def create_local_input_stream(self) -> int:
        """
        Parses the input settings and then passes control
        """
        if self.args.input == "-":
            return self.create_local_output_stream(sys.stdin.readline)
        # else
        with open(self.args.input, "r", encoding="utf-8") as infile:
            return self.create_local_output_stream(infile.readline)

    def create_serial_ports(self) -> int:
        """
        Create Serial Devices
        """
        # Determine Serial Device Settings
        bytesize, parity, stopbits = parse_serial_framing(self.args.framing)
        xonxoff, rtscts, dsrdtr = parse_serial_flow_control(self.args.flow_control)
        read_timeout = (16 * 12)/self.args.baud
        #read_timeout = 1

        # Create DCE port
        with serial.Serial(port=self.args.portname, baudrate=self.args.baud, bytesize=bytesize,
        parity=parity, stopbits=stopbits, xonxoff=xonxoff, rtscts=rtscts, dsrdtr=dsrdtr,
        timeout=read_timeout) as dce:
            self.dce=dce

            if self.args.mitm is None:
                return self.create_local_input_stream()

            # else Create DTE port, if needed
            with serial.Serial(port=self.args.mitm, baudrate=self.args.baud, bytesize=bytesize,
            parity=parity, stopbits=stopbits, xonxoff=xonxoff, rtscts=rtscts, dsrdtr=dsrdtr,
            timeout=read_timeout) as dte:
                self.dte=dte

                return self.create_local_input_stream()
        self.shutdown.set()
        return -1


    def run(self) -> int:
        """
        Entry point for passing control to the Hexterm
        """
        self.shutdown.clear()
        print(str(self.args).replace("Namespace","Settings",1))
        print("Type 'quit' to exit")

        # create Serial Device
        return self.create_serial_ports()

def verify_args_skip_start(args: 'argparse.Namespace') -> bool:
    '''
        Verifies args for correctness.
        returns True if starting the program should be skipped
    '''
    if args.forward and not args.mitm:
        print('Forwarding cannot be enabled outside of monitor (mitm) mode.')
        return True

    if isinstance(args.baud, str) and args.baud.upper() in ['HELP', '?', 'H']:
        print(
        "Baud rate is an integer number of bit clocks per second                        \n"
        "                                                                               \n"
        "The bits per second clock rate setting for the serial port.                    \n"
        "Depending on the framing parameters the bytes per second will max out          \n"
        "at about a tenth this value.                                                   \n"
        "There may be limits on what rate your serial port hardware can support.        \n"
        "The most common baud rate when speed is not essential is:                      \n"
        "    9600 (DEFAULT)                                                             \n"
        "Most common baud rates:                                                        \n"
        "    1200, 2400, 4800, 19200, 38400, 57600, and 115200                          \n"
        "Common older baud rates:                                                       \n"
        "    50, 75, 110, 150, 300, and 600                                             \n"
        "    130, 1800, 3600, and 7200                                                  \n"
        "Newer baud rates:                                                              \n"
        "    230400, and 460800                                                         \n"
        "    128000, 256000, and 921600                                                 \n"
        )
        return True

    if args.framing.upper() in ['HELP', '?', 'H']:
        print(
        "Format: <DATABITS[5-8]><PARITY[EMNOS]><STOPBITS[1,1.5,2]>                      \n"
        "                                                                               \n"
        "The framing indicates how the data bits are put on the wire.                   \n"
        "The data bits are sent with a framing of:                                      \n"
        "    1) a single start bit                                                      \n"
        "    2) Some number of data bits (usually 5-8)                                  \n"
        "    3) Optionally a parity bit of various formats for verification purposes    \n"
        "    4) Some number of stop bits (usually 1-1.5)                                \n"
        "The highest throughtput and most common framing sends the 8 date bit with the  \n"
        "minimum framing of 1 start bit and 1 stop bit, resulting in taking only 10 bit \n"
        "times to send an 8-bit data byte.                                              \n"
        "It is common to express these formats in compressed strings in which the first \n"
        "number is the number of data bits, then a single character to indicate parity  \n"
        "calculation then a number to indicate how many stop bits.                      \n"
        "Thus the default '8N1' means 8 data bits, no parity bits and 1 stop bit.       \n"
        "5 bit codes such as Baudot and ITA-2 we once very common 5N1.                  \n"
        "ASCII is a 7-bit code so was sometimes sent with 'free' parity bits '7E1'.     \n"
        "HW may or may not actually respect parity checks. it may just strip it off.    \n"
        "Parity options:                                                                \n"
        "    N - No parity bit sent                                                     \n"
        "    E - Even, parity bit makes sure an even number of 1s are always sent       \n"
        "    O - Odd, parity bit makes sure an odd number of 1s are always sent         \n"
        "    M - The parity bit is sent, but is always a 1                              \n"
        "    S - The parity bit is sent, but is always a 0                              \n"
        )
        return True

    if args.encoding.upper() in ['HELP', '?', 'H']:
        print(
        "Encoding to use on the serial data to make the raw bytes readable.             \n"
        "Hexterm defaults to the Code Page 437 encoding used on early IBM PCs and       \n"
        "common to many 16-bit era protocols.                                           \n"
        "Historically, many different encoding were used on serial data.                \n"
        "Hexterm supports any encoding supportted by your version of python:            \n"
        "    https://docs.python.org/library/codecs.html#standard-encodings             \n"
        "Common alternative selections for encoding include:                            \n"
        "    cp037    - popular non-ascii EBCDIC encoding from IBM covering latin-1     \n"
        "    ascii    - Old standard 7-bit encoding commonly extended                   \n"
        "    cp437    - extended ASCII encoding of the original IBM/MS-DOS PC (DEFAULT) \n"
        "    latin-1  - extended ASCII encoding specified in ISO8859-1                  \n"
        "    cp1252   - extended latin-1 encoding, common used on MS Windows            \n"
        "    utf-8    - standard multi-byte encoding that is fully ASCII compatible     \n"
        "    mbcs     - encoding similar to utf-8 only uses on MS Windows               \n"
        )
        return True

    if args.flow_control.upper() in ['HELP', '?', 'H']:
        print(
        "Serial supports several flow control modes. If in doubt leave it with None.    \n"
        "Flow control allows the devices to coordinate when they are ready for data to  \n"
        "be sent. Some serial HW may not support some of the signalling for some        \n"
        " versions of HW flow control.                                                  \n"
        "Options:                                                                       \n"
        "    none     - No flow control is performed (DEFAULT)                          \n"
        "    sw       - The XON(0x11) and XOFF(0x13) bytes provide SW flow control      \n"
        "    hw       - Alias for RTS and CTS the common variant of HW flow control     \n"
        "    rts, cts - uses RTS and CTS signals to control HW flow control             \n"
        "    dtr, dsr - uses DTR and DSR signals to control HW flow control             \n"
        "    sw/hw    - Enables XON/XOFF and RTS/CTS Flow Control                       \n"
        "    sw/dtr   - Enables XON/XOFF and DTR/DSR Flow Control                       \n"
        "    all      - Enables all flow control methods                                \n"
        )
        return True

    return False

def check_baud_type( baud ):
    """
    Allows baud to either be an integer or request help
    """
    if baud.upper() in ['HELP', '?', 'H']:
        return baud
    return int(baud)


def print_encoding_table( encoding ):
    """
    prints the encoding table for a given encoder.
    """
    for i in range(0,256,16):
        data = bytearray(range(i,i+16))
        print(convert_16bytes_to_string(data, encoding))

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
        metavar='BAUDRATE',  type=check_baud_type, default=9600,
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
    parser.add_argument('-m','--mitm', '--monitor',
        metavar='PORT',
        help='enables monitor-in-the-middle protocol analyzer mode, repeats data to/from PORT')

    parser.set_defaults(forward=None)
    parser.add_argument('--nf', '--no-f', '--no-forwarding',
        dest='forward', action='store_false',
        help='turns off the mitm forwarding. useful for split cable operation')

    parser.set_defaults(timestamp=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ts', '--timestamp',
        dest='timestamp', action='store_true',
        help='')
    group.add_argument('--no-ts', '--no-timestamp',
        dest='timestamp', action='store_false',
        help='turns on/off prepending of timestamps to the entries')

    args = parser.parse_args()

    if verify_args_skip_start(args):
        return 0

    hexterm = HexTerm( args )

    return hexterm.run()


if __name__ == '__main__':
    sys.exit(main())


#
#
#  io ports:
#   port - dce
#   mitm - dte
#   local
#
#  Threads:
#    local_rx_thread - initial main thread, takes "user" input, parses CLI
#    dce_rx_thread - takes bytes from DCE, converts to Human readable form
#    dte_rx_thread - takes bytes from DTE in mitm mode, converts to Human readable form
#    <TBD> 2 output_worker_thread - background thread to take over conversion to Human readable form
#  1 mutex for each output
