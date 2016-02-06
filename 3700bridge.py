#!/usr/bin/python -u
# The -u makes output unbuffered, so it will show up immediately
import sys
import socket
import select
import json
import datetime


# pads the name with null bytes at the end
def pad(name):
    result = '\0' + name
    while len(result) < 108:
        result += '\0'
    return result

# form the bpdu to be sent
def form_bpdu(id, rt, cost):
    return json.dumps({'source': id, 'dest': 'ffff', 'type': 'bpdu',
                       'message':{'root': rt, 'cost': cost}})

# creates bridge
def main(argv):

    # A BPDU
    class BDPU:
        def __init__(self, designated_bridge, rt_port, rt, cost):
            self.id = designated_bridge
            self.rt_port = rt_port
            self.rt = rt
            self.cost = cost

    # argc check
    if len(argv) < 2:
        raise ValueError('Bridge must have id and connect to LAN')

    id = argv[0]
    # initial lan addresses
    lan_args = argv[1:]
    # list of ports
    ports = []
    # map of file descriptor to ports
    file_no_to_port = {}
    # map of ports to lan number
    port_to_lan = {}
    # map of lans to ports
    lan_to_port = {}
    # port activation status
    ports_on = {}
    # stored BPDU
    # assume self is the root
    bpdu = BDPU(id, 0, id, 0)
    time_out = datetime.datetime.now()

    # creates ports and connects to them
    for x in range(len(lan_args)):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        s.connect(pad(lan_args[x]))
        ports.append(s)
        port_to_lan[s] = lan_args[x]
        file_no_to_port[s.fileno] = s
        lan_to_port[lan_args[x]] = s
        ports_on[s] = True


    # ready
    print "Bridge " + id + " starting up\n"

    # Main loop
    while True:
        # Calls select with all the ports; change the timeout value (1)
        ready_read, ready_write, ignore2 = select.select(ports, ports, [], 1)

        # Reads from each of the ready ports
        for x in ready_read:
            json_data = x.recv(1500)
            data = json.loads(json_data)
            src = data['source']
            dest = data['dest']
            type = data['type']
            full_msg = data['message']
            if type == 'data':
                id = full_msg['id']
                print 'Received Message {} on port {} from {} to {}'.format(id, x.fileno(), src, dest)
            elif type == 'bpdu':
                print 'Received BPDU {} on port {} from {} to {}'.format(id, x.fileno(), src, dest)
                rt = full_msg['root']
                cost = full_msg['cost']
                if rt < bpdu.rt \
                        or (rt == bpdu.rt and (cost < (bpdu.cost - 1))) \
                        or (rt == bpdu.rt and (cost == bpdu.cost - 1) and src < bpdu.id):
                    bpdu = BDPU(src, x.fileno(), rt, cost + 1)

            #print json_data
            #print bpdu.rt
            #print bpdu.cost

        # BPDU send timer
        time_diff = datetime.datetime.now() - time_out
        total_milliseconds = time_diff.total_seconds() * 1000
        if total_milliseconds > 750:
            time_out = datetime.datetime.now()
            for x in ready_write:
                x.send(form_bpdu(id, bpdu.rt, bpdu.cost))


if __name__ == "__main__":
    main(sys.argv[1:])