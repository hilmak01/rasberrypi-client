#!/usr/bin/env python3

import struct

with open ("data0.bin","rb") as file:
    d=file.read()

n=0
p=[]
while n<(len(d)-1):
    p.append(struct.unpack("<h",d[n:n+2])[0]) # little endian, short integer
    n=n+2

# print(p)
