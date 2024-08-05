# hexterm
A raw hexadecimal based terminal emulator for monitoring binary serial interfaces.

## Usage
```
usage: hexterm.py [-h] [-b BAUDRATE] [-c METHOD] [-e CODEC] [-f 8N1]
                  [-i FILENAME] [-o FILENAME] [-m PORT] [--nf] [--ts | --no-ts]
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
  --nf, --no-f, --no-forwarding
                        turns off the mitm forwarding. useful for split cable operation
  --ts, --timestamp
  --no-ts, --no-timestamp
                        turns on/off prepending of timestamps to the entries
```

### MITM Mode

Monitor-in-the-middle is a mode of operation in which hexterm uses two serial
ports to sit between a two serial devices (nominally the DCE and DTE) in order
to monitor their communications or inject messages.

While in this mode the two serial ports are configured with the same settings.
Any data received on either port is sent on the other. These messages will be
shown in hexterm as normal with a prefix indicating direction whether it was
DTE to DCE "T -> C" or DCE to DTE "T <- C". Using this with timestamps is a
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

#### Low Latency Monitor-only Mode
There is an alternative that allows the DTE and DCE to communicate fully in
real-time, at the expense of losing the ability to inject our own data. This
may be needed for systems running at higher baud rates, or systems that rely on
the latency of the serial exchange. To do this wire the DTE straight to the DCE,
but tap off the GND(pin5), TxD(pin3) and RxD(pin2) lines from the cable feed
them into the RxD lines on 2 ports on the Monitor PC, this may require some
custom cabling. With this change hexterm no longer needs to forward between the
serial ports, though it does still need to monitor and interleave both:
```
                         +----------+
                         |   MITM   |
                         |COM2  COM1|
               +---------|Pin2  Pin2|------+
               |    +----|Pin5  Pin5|---+  |
               |    |    +----------+   |  |
               |    |                   |  |
               |    +-+-----------------+  |
+-------+      |      |      +-------------+  +--------+
| Host  |  Pin3|  Pin5|  Pin2|                | Device |
| (DTE) |------+------+------+----------------| (DCE)  |
+-------+                                     +--------+

./hexterm.py COM1 --mitm COM2 -b 115200 --no-forwarding

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
- [x] Add `--baud help`
- [x] Add `--encoding help`
- [x] Add `--flow-control help`
- [x] Add `--framing help`
- [ ] Standardize CLI options and descriptions a little (dd, gcc, cu, minicom)
- [x] Add I/O processing delay in script modes
- [x] handle single digit bytes when white space separated
- [x] Add monitor port for serial protocol analyzer type mitm mode
- [ ] align format more with plantUML sequence diagram in mitm mode (needs timestamp extension to plantUml sequence diagrams)
- [x] Add requirements.txt file
- [x] Add message timestamps command line option
- [x] Reduce mitm latency: create separate thread for output formatting
- [ ] Consider using asyncio instead of threads
- [ ] streamline byte to message group timing
- [ ] add protocol grouping options (timeout, separator(newline), regex, size field(1 byte?))
- [ ] local echo
- [ ] build real input syntax parser (regex, BNF, convert_string_to_bytes, local_input_loop)
- [ ] replace print with local writes or sys.stderr
