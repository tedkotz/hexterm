# hexterm
A raw hexadecimal based terminal emulator for monitoring binary serial interfaces.

## Usage
```
usage: hexterm.py [-h] [-b BAUDRATE] [-c METHOD] [-e CODEC] [-f 8N1] PORT

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
                        sets framing parameters in <DATABITS><PARITY><STOPBITS> form, default 8N1

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
- [ ] File I/O support
- [ ] Mixed hex and string input
- [ ] Use serial parameters
- [ ] Add doc strings to all functions
