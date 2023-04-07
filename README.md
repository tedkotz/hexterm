# hexterm
A raw hexadecimal based terminal emulator for monitoring binary serial interfaces.

## Usage
```
usage: hexterm.py [-h] [-b BAUDRATE] [-c METHOD] [-e CODEC] [-f 8N1]
                  [-i FILENAME] [-o FILENAME]
                  PORT

Raw hexadecimal based terminal emulator for monitoring binary serial interfaces

positional arguments:
  PORT                  uses named PORT

optional arguments:
  -h, --help            show this help message and exit
  -b BAUDRATE, --baud BAUDRATE, --speed BAUDRATE
                        sets the ports BUADRATE, default 9600
  -c METHOD, --flow-control METHOD, --control METHOD
                        sets flow control METHOD [HW:(RTS/CTS), SW:(XON/XOFF), None:(default)]
  -e CODEC, --encoding CODEC
                        sets encoding CODEC(ascii, latin-1, utf-8, etc), default cp437
  -f 8N1, --framing 8N1
                        sets framing parameters in <DATABITS[5-8]> <PARITY[EMNOS]> <STOPBITS[1,1.5,2]> form, default 8N1
  -i FILENAME, --input FILENAME
                        input is read from FILENAME
  -o FILENAME, --output FILENAME
                        output is appended to FILENAME
```

## Dependencies
- python3
- pyserial
- Maybe readline

## ToDo
- [x] Input thread
- [x] Output thread
- [x] Input formatting
- [x] Output parsing
- [x] File I/O support
- [x] Mixed hex and string input
- [x] Use serial parameters
- [ ] Add doc strings to all functions
- [ ] Add `help` command
- [ ] Add `--encoding help`
- [ ] Add `--flow-control help`
- [ ] Add `--framing help`
- [ ] Standardize CLI options and descriptions a little (dd, gcc, cu, minicom)
- [ ] Add I/O processing delay in script modes
