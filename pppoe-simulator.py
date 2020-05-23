from scapy.all import *
from scapy.layers.ppp import *

# In most cases you just have to change this:
interface = "en7"


ac_name = "PPPoE-Simulator"
service_name = ""
magic_number = 0xDEADBEEF
host_uniq = session_id = ac_cookie = mac_router = mac_server = eth_discovery = eth_session = None
ident = 0

End_Of_List = 0x0000
Service_Name = 0x0101
AC_Name = 0x0102
Host_Uniq = 0x0103
AC_Cookie = 0x0104
Vendor_Specific = 0x0105
Relay_Session_Id = 0x0110
Service_Name_Error = 0x0201
AC_System_Error = 0x0202
Generic_Error = 0x0203

PADI = 0x09
PADO = 0x07
PADR = 0x19
PADS = 0x65
PADT = 0xa7

LCP = 0xc021
PAP = 0xc023
CHAP = 0xc223
IPCP = 0x8021
IPV6CP = 0x8057
PPPoE_Discovery = 0x8863
PPPoE_Session = 0x8864

Configure_Request = 1
Configure_Ack = 2
Authenticate_Ack = 2
Configure_Nak = 3
Configure_Reject = 4
Terminate_Request = 5
Terminate_Ack = 6
Code_Reject = 7
Protocol_Reject = 8
Echo_Request = 9
Echo_Reply = 10
Discard_Request = 11


def packet_callback(pkt):
    global host_uniq, session_id, ident, ac_cookie, mac_router, mac_server, eth_discovery, eth_session
    mac_router = pkt[Ether].src
    eth_discovery = Ether(src=mac_server, dst=mac_router, type=PPPoE_Discovery)
    eth_session = Ether(src=mac_server, dst=mac_router, type=PPPoE_Session)

    if pkt.haslayer(PPPoED):
        if pkt[PPPoED].code == PADI:
            session_id = pkt[PPPoED].fields['sessionid']
            ac_cookie = os.urandom(20)
            for tag in pkt[PPPoED][PPPoED_Tags].tag_list:
                if tag.tag_type == Host_Uniq:
                    host_uniq = tag.tag_value
            print("Client->Server   |   Discovery Initiation")
            print("Server->Client   |   Discovery Offer")
            sendp(eth_discovery /
                  PPPoED(code=PADO, sessionid=0) /
                  PPPoETag(tag_type=Service_Name, tag_value=service_name) /
                  PPPoETag(tag_type=AC_Name, tag_value=ac_name) /
                  PPPoETag(tag_type=AC_Cookie, tag_value=ac_cookie) /
                  PPPoETag(tag_type=Host_Uniq, tag_value=host_uniq))
        elif pkt[PPPoED].code == PADR:
            print("Client->Server   |   Discovery Request")
            print("Server->Client   |   Discovery Session-confirmation")
            session_id = os.urandom(2)[0]
            sendp(eth_discovery /
                  PPPoED(code=PADS, sessionid=session_id) /
                  PPPoETag(tag_type=Service_Name, tag_value=service_name) /
                  PPPoETag(tag_type=Host_Uniq, tag_value=host_uniq))
            print("Server->Client   |   Configuration Request (PAP)")
            sendp(eth_session /
                  PPPoE(sessionid=session_id) /
                  PPP(proto=LCP) /
                  PPP_LCP(code=Configure_Request, id=ident + 1, data=(Raw(PPP_LCP_MRU_Option(max_recv_unit=1492)) /
                                                                      Raw(PPP_LCP_Auth_Protocol_Option(
                                                                       auth_protocol=PAP)) /
                                                                      Raw(PPP_LCP_Magic_Number_Option(
                                                                       magic_number=magic_number)))))

    elif pkt.haslayer(PPPoE) and pkt.haslayer(PPP):
        if pkt[PPPoE].sessionid != 0:
            session_id = pkt[PPPoE].sessionid
        if pkt.haslayer(PPP_LCP_Configure):
            ppp_lcp = pkt[PPP_LCP_Configure]
            if pkt[PPP_LCP_Configure].code == Configure_Request:
                ident = pkt[PPP_LCP_Configure].id
                print("Client->Server   |   Configuration Request (MRU)")
                print("Server->Client   |   Configuration Ack (MRU)")
                sendp(eth_session /
                      PPPoE(sessionid=session_id) /
                      PPP(proto=LCP) /
                      PPP_LCP(code=Configure_Ack, id=ident, data=(Raw(PPP_LCP_MRU_Option(max_recv_unit=1480)) /
                                                                  Raw(ppp_lcp[PPP_LCP_Magic_Number_Option]))))
            elif pkt[PPP_LCP_Configure].code == Configure_Ack:
                print("Client->Server   |   Configuration Ack")
                print("Server->Client   |   Echo Request")
                sendp(eth_session /
                      PPPoE(sessionid=session_id) /
                      PPP(proto=LCP) /
                      PPP_LCP_Echo(code=Echo_Request, id=ident + 1, magic_number=magic_number))
        elif pkt.haslayer(PPP_LCP_Echo):
            if pkt[PPP_LCP_Echo].code == Echo_Request:
                ident = pkt[PPP_LCP_Echo].id
                print("Client->Server   |   Echo Request")
                print("Server->Client   |   Echo Reply")
                sendp(eth_session /
                      PPPoE(sessionid=session_id) /
                      PPP(proto=LCP) /
                      PPP_LCP_Echo(code=Echo_Reply, id=ident, magic_number=magic_number))
        elif pkt.haslayer(PPP_PAP_Request):
            ident = pkt[PPP_PAP_Request].id
            print("Client->Server   |   Authentication Request")
            print("Server->Client   |   Authenticate Ack")
            sendp(eth_session /
                  PPPoE(sessionid=session_id) /
                  PPP(proto=PAP) /
                  PPP_PAP_Response(code=Authenticate_Ack, id=ident, message="Login ok"))
            print("Server->Client   |   Configuration Request (IP)")
            sendp(eth_session /
                  PPPoE(sessionid=session_id) /
                  PPP(proto=IPCP) /
                  PPP_IPCP(code=Configure_Request, id=ident + 1, options=PPP_IPCP_Option_IPAddress(data="10.15.0.8")))
        elif pkt.haslayer(PPP_IPCP):
            ident = pkt[PPP_IPCP].id
            if pkt[PPP_IPCP].options[0].data == "0.0.0.0":
                options = [PPP_IPCP_Option_IPAddress(data="10.16.0.9"),
                           PPP_IPCP_Option_DNS1(data="114.114.114.114"),
                           PPP_IPCP_Option_DNS2(data="114.114.114.114")]
                print("Client->Server   |   Configuration Request (invalid)")
                print("Server->Client   |   Configuration Nak")
                sendp(eth_session /
                      PPPoE(sessionid=session_id) /
                      PPP(proto=IPCP) /
                      PPP_IPCP(code=Configure_Nak, id=ident, options=options))
            else:
                print("Client->Server   |   Configuration Request (valid)")
                print("Server->Client   |   Configuration Ack")
                sendp(eth_session /
                      PPPoE(sessionid=session_id) /
                      PPP(proto=IPCP) /
                      PPP_IPCP(code=Configure_Ack, id=ident, options=pkt[PPP_IPCP].options))
        if pkt[PPP].proto == IPV6CP:
            print("Client->Server   |   Configuration Request IPV6CP")
            print("Server->Client   |   Protocol Reject IPV6CP")
            sendp(eth_session /
                  PPPoE(sessionid=session_id) /
                  PPP(proto=LCP) /
                  PPP_LCP_Protocol_Reject(code=Protocol_Reject, id=ident + 1, rejected_protocol=IPV6CP,
                                          rejected_information=pkt[PPP].payload))


def terminateConnection():
    print("Server->Client   |   Terminate Connection")
    sendp(eth_session /
          PPPoE(sessionid=session_id) /
          PPP(proto=LCP) /
          PPP_LCP_Terminate())


def isNotOutgoing(pkt):
    if pkt.haslayer(Ether):
        return pkt[Ether].src != mac_server
    return False


if __name__ == '__main__':
    conf.verb = 0  # Suppress Scapy output
    conf.iface = interface  # Set default interface
    mac_server = get_if_hwaddr(interface)
    print("Waiting for packets")
    sniff(prn=packet_callback, filter="pppoed or pppoes", lfilter=isNotOutgoing)
