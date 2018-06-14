from scapy.layers.inet import *
from scapy.sendrecv import *
import json
import requests
import socket

SERVER_PORT = 8200
BOSS_IP = "127.0.0.1"
NUM_OF_PACKETS = 200
IP_API = "http://ip-api.com/json/"
MACHINE_IP = ""

ip_locations = {}
packet_list = []  # the list is being erased every NUM_OF_PACKETS times


def main():
    global MACHINE_IP
    global packet_list
    MACHINE_IP = get_ip()  # assign the machine ip
    init()
    while True:  # the function runs forever
        packet_list = []
        sniff(lfilter=sniff_filter, prn=process_packet, count=NUM_OF_PACKETS)
        print("Done.\nPerforming location lookup.")
        get_ip_location()
        print("Sending information to server")
        try:
            send_to_boss()
        except Exception:
            print("Failed to send. Trying again")
            send_to_boss()
            print("Couldn't reach server. May be offline. Program is being terminated")
        print("Done. Proceeding to the next round\n")


def sniff_filter(packet):
    """
    the function checks if the packet given is udp or tcp and above ip layer (only Ipv4 otherwise the program crashes)
    in addition, it makes sure that the packet is from or to this machine (not in promisc mouse)
    :param packet: the packet to check
    :return: true if the packet is valid, false otherwise
    :rtype: bool
    """
    if IP in packet:
        if packet[IP].src == MACHINE_IP or packet[IP].dst == MACHINE_IP:
            if TCP in packet or UDP in packet:
                return True
    else:
        return False


def process_packet(packet):
    """
    The function receive a packet and analyzes it and puts it in a dictionary, then appends it to the global packet list
    :param packet: the packet to analyze
    :type packet: packet
    :return: None
    """
    #  find packet type:
    temp_dict = {}
    if TCP in packet:
        p_type = packet[TCP]
    else:
        p_type = packet[UDP]
    # find the IP of the server
    if packet[IP].src == MACHINE_IP:
        packet_dst = packet[IP].dst
        temp_dict["outgoing"] = True
        temp_dict["dport"] = p_type.dport
    else:
        packet_dst = packet[IP].src
        temp_dict["outgoing"] = False
        temp_dict["dport"] = p_type.sport
    print(str(packet[IP].src) + ":" + str(p_type.sport) + " ==> " + str(packet[IP].dst) + ":" + str(p_type.dport))

    temp_dict["ip"] = packet_dst
    temp_dict["size"] = len(packet)

    packet_list.append(temp_dict)  # add the packet information to the global packet list


def init():
    """
    The function prints some basic information to the user
    :return: None
    """
    global BOSS_IP
    global NUM_OF_PACKETS
    print("Welcome to BossSniffer agent! Let's verify some information before we begin.")
    print("The IP of the boss: " + BOSS_IP)
    print("The port: " + str(SERVER_PORT))
    print("The number of packets per cycle: " + str(NUM_OF_PACKETS))
    print("You can modify these values. Type \'IP\' to modify the IP, type \'PACKS\' to modify the number packet per round, or press enter to user defaults. ")
    choice = input()
    if choice == "IP":
        BOSS_IP = input("Enter new IP: ")
        print("Press enter to continue or type \'PACKS\' to modify the number of packs per round")
        choice = input()
        if choice == "PACKS":
            NUM_OF_PACKETS = int(input("Enter new number of packs per round: "))

    elif choice == "PACKS":
        NUM_OF_PACKETS = input("Enter new number of packs per round: ")
        print("Press enter to continue or type \'IP\' to modify the IP of the server")
        choice = input()
        if choice == "IP":
            NUM_OF_PACKETS = int(input("Enter new server IP: "))
    print("All set! You can stop the sniffer anytime by pressing {0}! Press enter to start.".format("Ctrl+C"))
    choice = input()


def get_ip_location():
    """
    The function finds locations of given IP. if the lookup fails (mostly because of private ips in the same subnet) location replaced with unknown location string
    :return: None
    """
    for packet in packet_list:
        if packet["ip"] in ip_locations.keys():  # if the ip is in the dictionary, we know its location
            packet["country"] = ip_locations[packet["ip"]]
        else:
            response = requests.get(IP_API + packet["ip"])
            html = response.json()
            if "fail" not in html.values():  # if the operation succeeded
                ip_locations[packet["ip"]] = html["country"]
                packet["country"] = ip_locations[packet["ip"]]
            else:  # the location lookup failed.
                ip_locations[packet["ip"]] = "unknown location"
                packet["country"] = ip_locations[packet["ip"]]


def send_to_boss():
    """
    The function sends report to the boss.
    :return: None
    """
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print()
    data = json.dumps(packet_list)
    connection.sendto(data.encode(), (BOSS_IP, SERVER_PORT))
    connection.close()


def get_ip():
    """
    The function returns the ip of the machine. supports both windows and linux
    :return: the ip of the machine
    :rtype: str
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 0))
    address = s.getsockname()[0]
    s.close()
    return address


if __name__ == '__main__':
    main()
