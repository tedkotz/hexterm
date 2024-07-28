# hexterm
A raw hexadecimal based terminal emulator for monitoring binary serial interfaces.

## Usage
```
usage: hexterm.py [-h] [-b BAUDRATE] [-c METHOD] [-e CODEC] [-f 8N1]
                  [-i FILENAME] [-o FILENAME] [-m PORT]
                  PORT

Raw hexadecimal based terminal emulator for monitoring binary serial interfaces

positional arguments:
  PORT                  uses named PORT

options:
  -h, --help            show this help message and exit
  -b BAUDRATE, --baud BAUDRATE, --speed BAUDRATE
                        sets the ports BUADRATE, default 9600
  -c METHOD, --flow-control METHOD, --control METHOD
                        sets flow control METHOD [HW:(RTS/CTS), SW:(XON/XOFF), None:(default)]
  -e CODEC, --encoding CODEC
                        sets encoding CODEC(ascii, latin-1, utf-8, etc), default cp437
  -f 8N1, --framing 8N1
                        sets framing in <DATABITS[5-8]><PARITY[EMNOS]><STOPBITS[1,1.5,2]> form, default 8N1
  -i FILENAME, --input FILENAME
                        input is read from FILENAME
  -o FILENAME, --output FILENAME
                        output is appended to FILENAME
  -m PORT, --mitm PORT, --monitor PORT
                        enables monitor-in-the-middle protocol analyzer mode, repeats data to/from PORT
```

### MITM Mode

Monitor-in-the-middle is a mode of operation in which hexterm uses two serial
ports to sit between a two serial devices (nominally the DCE and DTE) in order
to monitor their communications or inject messages.

While in this mode the two serial ports are configured with the same settings.
Any data received on either port is sent on the other. These messages will be
shown in hexterm as normal with a prefix indicating direction whether it was
DTE to DCE "T-->C" or DCE to DTE "T<--C". Using this with timestamps is a
great way to capture the sequence of a protocol.

Messages entered into hexterm in MITM mode will default to being sent to the DCE
like normal. However a message prefixed with a 't' will instead be sent to the
DTE.

This can be used to analyze serial protocols for reverse engineering, debugging
or embedded development.

This may require a bunch of serial ports, cables and null modems if the computer
running the monitor is also driving the device. In the simple case, a null modem
is probably needed. Here is an example:

```
+-------+                +----------+         +--------+
| Host  |                |   MITM   |         | Device |
| (DTE) |--[Null Modem]--|COM2  COM1|---------| (DCE)  |
+-------+                +----------+         +--------+

./hexterm.py COM1 --mitm COM2 -b 9600

```

## Dependencies
- python3
- pyserial
- Maybe prompt_toolkit

## ToDo
- [x] Input thread
- [x] Output thread
- [x] Input formatting
- [x] Output parsing
- [x] File I/O support
- [x] Mixed hex and string input
- [x] Use serial parameters
- [x] Add doc strings to all functions
- [x] Add `help` command
- [ ] Add `--encoding help`
- [ ] Add `--flow-control help`
- [ ] Add `--framing help`
- [ ] Standardize CLI options and descriptions a little (dd, gcc, cu, minicom)
- [ ] Add I/O processing delay in script modes
- [ ] Consider using asyncio instead of threads
- [ ] handle single digit bytes when white space separated
- [x] Add monitor port for serial protocol analyzer type mitm mode
- [ ] Add requirements.txt file
- [ ] Add message timestamps
