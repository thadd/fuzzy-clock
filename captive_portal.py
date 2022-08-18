"""
Heavily customized custom captive portal for fuzzy clock

Taken from:
* License: MIT
* Repository: https://github.com/metachris/micropython-captiveportal
* Author: Chris Hager <chris@linuxuser.at> / https://twitter.com/metachris
"""
import gc
import sys
import network
import socket
import uasyncio as asyncio
import string
import json
import re
import query_string
import machine

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)


# Access point settings
SERVER_SSID = 'FuzzyClock'

def _handle_exception(loop, context):
    """ uasyncio v3 only: global exception handler """
    print('Global exception handler')
    sys.print_exception(context["exception"])
    sys.exit()

def process_user_wifi_settings(body):
    wifi_settings = query_string.parse(body)

    wifi_file = open('wifi.json', 'w')
    json.dump(wifi_settings, wifi_file)

    return wifi_settings

class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        tipo = (data[2] >> 3) & 15  # Opcode bits
        if tipo == 0:  # Standard query
            ini = 12
            lon = data[ini]
            while lon != 0:
                self.domain += data[ini + 1:ini + lon + 1].decode('utf-8') + '.'
                ini += lon + 1
                lon = data[ini]
        # print("DNSQuery domain:" + self.domain)

    def response(self, ip):
        # print("DNSQuery response: {} ==> {}".format(self.domain, ip))
        if self.domain:
            packet = self.data[:2] + b'\x81\x80'
            packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'  # Questions and Answers Counts
            packet += self.data[12:]  # Original Domain Name Question
            packet += b'\xC0\x0C'  # Pointer to domain name
            packet += b'\x00\x01\x00\x01\x00\x00\x00\x3C\x00\x04'  # Response type, ttl and resource data length -> 4 bytes
            packet += bytes(map(int, ip.split('.')))  # 4bytes of IP
        # print(packet)
        return packet


class MyApp:
    async def start(self):
        # Get the event loop
        loop = asyncio.get_event_loop()

        # Add global exception handler
        if IS_UASYNCIO_V3:
            loop.set_exception_handler(_handle_exception)

        # Start the wifi AP
        self.wifi_start_access_point()

        # Create the server and add task to event loop
        server = asyncio.start_server(self.handle_http_connection, "0.0.0.0", 80)
        loop.create_task(server)

        # Start the DNS server task
        loop.create_task(self.run_dns_server())

        # Start looping forever
        print('Interface ready...')
        loop.run_forever()

    def wifi_start_access_point(self):
        wifi = network.WLAN(network.AP_IF)

        found_networks = wifi.scan()

        wifi.config(ssid=SERVER_SSID, security=0)
        wifi.active(True)

        while wifi.active() == False:
          pass

        # We need to reset any DNS options the wifi may have cached
        ifconfig = wifi.ifconfig()
        self.server_ip = ifconfig[0]
        wifi.ifconfig([self.server_ip, ifconfig[1], ifconfig[2], self.server_ip])
        print('AP set up, network config:', wifi.ifconfig())

        # Find the real networks
        self.available_networks = set()
        for found_net in found_networks:
            net_name = found_net[0].decode()
            if all(c in string.printable for c in net_name) and len(net_name) != 0:
                self.available_networks.add(net_name)

        print('networks {}'.format(self.available_networks))

    async def handle_http_connection(self, reader, writer):
        gc.collect()

        should_reboot = False

        # Get HTTP request line
        data = await reader.readline()
        request_line = data.decode()
        addr = writer.get_extra_info('peername')
        print('Received {} from {}'.format(request_line.strip(), addr))

        # Read the whole request
        headers = request_line
        while True:
            gc.collect()
            line = await reader.readline()
            headers += line.decode()
            if line == b'\r\n': break

        # Handle the request
        if len(request_line) > 0:            
            # Get the path the client wants
            path = request_line.split()[1]

            # See if a file matching the path exists
            try:
                response = 'HTTP/1.0 200 OK\r\n\r\n'

                filename = path.replace('/', '', 1)

                with open(filename) as f:
                    response += f.read()

                print('  Sent {}'.format(filename))

            except Exception as reason:
                # Sending us wifi connection details
                if path.startswith("/setup"):
                    response = 'HTTP/1.0 201 OK\r\n\r\n'

                    # Figure out how much more we have to read
                    content_length = int(re.search("Content-Length:\s*(\d+)", headers).group(1))

                    body_bytes = await reader.read(content_length)
                    process_user_wifi_settings(body_bytes.decode())

                    with open('setup_complete.html') as f:
                        response += f.read()
                        print('  Sent setup_complete.html')

                    should_reboot = True
                else:
                    # No match, show index.html
                    response = 'HTTP/1.0 200 OK\r\n\r\n'
                    with open('index.html') as f:
                        response += f.read()

                        networks_html = str()
                        for net in self.available_networks:
                            networks_html = networks_html + '<option value="{}">{}</option>'.format(net, net)

                        response = response.format(available_networks=networks_html)

                        print('  Sent index.html')

            await writer.awrite(response)

        # Close the socket
        await writer.aclose()

        if should_reboot:
            await asyncio.sleep(5)
            machine.soft_reset()

    async def run_dns_server(self):
        """ function to handle incoming dns requests """
        udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udps.setblocking(False)
        udps.bind(('0.0.0.0', 53))

        while True:
            try:
                # gc.collect()
                if IS_UASYNCIO_V3:
                    yield asyncio.core._io_queue.queue_read(udps)
                else:
                    yield asyncio.IORead(udps)
                data, addr = udps.recvfrom(4096)
                # print("Incoming DNS request...")

                DNS = DNSQuery(data)
                udps.sendto(DNS.response(self.server_ip), addr)

                print("DNS Reply: {:s} -> {:s}".format(DNS.domain, self.server_ip))

            except Exception as e:
                print("DNS server error:", e)
                await asyncio.sleep_ms(3000)

        udps.close()

def start():
    # Main code entrypoint
    try:
        # Instantiate app and run
        myapp = MyApp()

        if IS_UASYNCIO_V3:
            asyncio.run(myapp.start())
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(myapp.start())

    except KeyboardInterrupt:
        print('Bye')

    finally:
        if IS_UASYNCIO_V3:
            asyncio.new_event_loop()  # Clear retained state
