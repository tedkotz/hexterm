# hexterm
A raw hexadecimal based terminal emulator for monitoring binary serial interfaces.

## Usage
```
usage: hexterm.py [-h] [-b BAUDRATE] [-f 8N1] [-c METHOD] PORT

Raw hexadecimal based terminal emulator for monitoring binary serial interfaces

positional arguments:
  PORT                  uses named PORT

optional arguments:
  -h, --help            show this help message and exit
  -b BAUDRATE, --baud BAUDRATE, --speed BAUDRATE
                        sets the ports BUADRATE, default 9600
  -f 8N1, --framing 8N1
                        sets framing parameters in
                        <DATABITS><PARITY><STOPBITS> form, default 8N1
  -c METHOD, --flow-control METHOD, --control METHOD
                        sets flow control METHOD [HW:(RTS/CTS), SW:(XON/XOFF),
                        None:(default)]
```

## Dependencies
- python3
- pyserial
- Maybe readline

## ToDo
- [x] Input thread
- [x] Output thread
- [ ] Input formatting
- [ ] Output parsing
- [ ] File I/O support
