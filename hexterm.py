#!/usr/bin/env python3

import threading
import io
import sys
import time

running = True;

def ConvertBytes2String(mybytes):
    return mybytes.decode()

def ConvertString2Bytes(mystring):
    return mystring.encode()

def Char2BytesLoop(charInput, bytesOutput):
    global running
    while running:
        time.sleep(1)
        line = charInput.readline()
        if line[0].upper() == "Q":
            running=False
        else:
            bytesOutput.write(ConvertString2Bytes(line))

def Bytes2CharLoop(bytesInput, charOutput):
    global running
    count=0
    while running:
        time.sleep(1)
        if count < 16:
            charOutput.write(ConvertBytes2String(bytesInput.read(1))+" ")
            ++count
        else:
            charOutput.write(ConvertBytes2String(bytesInput.read(1))+"\n")
            count=0



def mainloop():
    bbuf = io.BytesIO()
    b2c = threading.Thread(target=Bytes2CharLoop, args=(bbuf,sys.stdout))
    c2b = threading.Thread(target=Char2BytesLoop, args=(sys.stdin,bbuf))

    # Start both loops.
    b2c.start()
    c2b.start()

    # wait for join.
    b2c.join()
    c2b.join()

    print("Exiting")
    print(bbuf)


mainloop()

