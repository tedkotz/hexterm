#!/usr/bin/env python3

running = True;

def Char2BytesLoop():
    global running
    while running:
        line = charInput.readline()
        if line[0].upper == "Q":
            runnning=False
        else:
            bytesOutput.write(ConvertString2Bytes(line))

def Bytes2CharLoop():
    global running
    count=0
    while running:
        if count < 16:
            charOutput.write(ConvertBytes2String(bytesInput.read()), end=" ")
            ++count
        else:
            charOutput.write(ConvertBytes2String(bytesInput.read()))
            count=0



def mainloop(charInput, charOutput, bytesInput, bytesOutout):
     // Start both loops.
     // wait for join.


