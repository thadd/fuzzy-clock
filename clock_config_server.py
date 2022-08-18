import gc
import json
import network
import uasyncio as asyncio
import re
import query_string

def rgb_triplet_to_hex(triplet):
    r = hex(triplet[0])[2:] if triplet[0] != 0 else "00"
    g = hex(triplet[1])[2:] if triplet[1] != 0 else "00"
    b = hex(triplet[2])[2:] if triplet[2] != 0 else "00"

    if len(r) == 1: r = "0" + r
    if len(g) == 1: g = "0" + g
    if len(b) == 1: b = "0" + b

    return "#" + r + g + b

def rgb_hex_to_triplet(hexcolor):
    return [int(hexcolor[1:3], 16), int(hexcolor[3:5], 16), int(hexcolor[5:7], 16)]

async def load_wifi_settings():
    print('Loading wifi settings')

    wifi_file = open('wifi.json')

    wifi_settings = json.load(wifi_file)

    print("  Loaded: {}".format(wifi_settings))
    return wifi_settings

async def load_clock_config():
    # print('Loading clock config')

    config_file = open('config.json')

    clock_config = json.load(config_file)

    # print("  Loaded: {}".format(clock_config))
    return clock_config

async def save_clock_config(clock_config):
    # print('Saving clock config')

    config_file = open('config.json', 'w')

    json.dump(clock_config, config_file)

    config_file.close()

    # print("  Saved: {}".format(clock_config))
    return clock_config

async def connect_to_wifi(wifi_settings):
    print("Connecting to wifi")

    wlan = network.WLAN(network.STA_IF)
    # wlan.config(hostname='fuzzy-clock')
    wlan.active(True)
    wlan.connect(wifi_settings['network'], wifi_settings['passcode'])

    while wlan.isconnected() == False:
        print('  Waiting for connection...')
        await asyncio.sleep(1)

    print("  Connection success: {}".format(wlan.ifconfig()))
    return wlan

async def handle_http_connection(reader, writer):
    gc.collect()

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
            filename = path.replace('/', '', 1)

            with open(filename) as f:
                response = 'HTTP/1.0 200 OK\r\n\r\n'
                await writer.awrite(response)

                # We can't fit it all in memory at once so chunk it up
                while chunk := f.read(1024):
                    await writer.awrite(chunk)

            print('  Sent {}'.format(filename))

        except Exception as reason:
            try:
                replacements = {
                    'save_success_display': 'none'
                }

                # Sending us wifi connection details
                if path.startswith("/config"):
                    print('/config')

                    # Figure out how much more we have to read
                    content_length = int(re.search("Content-Length:\s*(\d+)", headers).group(1))

                    body_bytes = await reader.read(content_length)
                    
                    updated_settings = query_string.parse(body_bytes.decode())

                    offset = int(updated_settings['timeoffset'])
                    if updated_settings['timezone'] != 'other': offset = int(updated_settings['timezone'])

                    settings_to_save = {
                        'timezone_offset': offset,
                        'use_dst': 'use_dst' in updated_settings,
                        'change_times': {
                            'night_begins': int(updated_settings['nightstart']),
                            'night_ends': int(updated_settings['nightend'])
                        },
                        'theme': {
                            'day': {
                                'on': rgb_hex_to_triplet(updated_settings['day_foreground']),
                                'off': rgb_hex_to_triplet(updated_settings['day_background'])
                            },
                            'night': {
                                'on': rgb_hex_to_triplet(updated_settings['night_foreground']),
                                'off': rgb_hex_to_triplet(updated_settings['night_background'])
                            }
                        },
                        'fade_steps': int(updated_settings['fade_steps'])
                    }

                    await save_clock_config(settings_to_save)

                    replacements['save_success_display'] = 'block'
                
                # No match, show settings page
                response = 'HTTP/1.0 200 OK\r\n\r\n'

                with open('clock_settings.html') as f:
                    response += f.read()

                    clock_config = await load_clock_config()

                    is_other_tz = False
                    if (clock_config['timezone_offset'] < -10 or clock_config['timezone_offset'] > -5): is_other_tz = True

                    tz_html = str()
                    tz_html += "<option value='-8' {}>Pacific</option>".format("selected" if clock_config['timezone_offset'] == -8 else "")
                    tz_html += "<option value='-7' {}>Mountain</option>".format("selected" if clock_config['timezone_offset'] == -7 else "")
                    tz_html += "<option value='-6' {}>Central</option>".format("selected" if clock_config['timezone_offset'] == -6 else "")
                    tz_html += "<option value='-5' {}>Eastern</option>".format("selected" if clock_config['timezone_offset'] == -5 else "")
                    tz_html += "<option value='-9' {}>Alaska</option>".format("selected" if clock_config['timezone_offset'] == -9 else "")
                    tz_html += "<option value='-10' {}>Hawaii</option>".format("selected" if clock_config['timezone_offset'] == -10 else "")
                    tz_html += "<option value='other' {}>Other (click below to use this option)</option>".format("selected" if is_other_tz else "")

                    replacements['timezone_options'] = tz_html

                    replacements['use_dst'] = "checked" if clock_config['use_dst'] else ""

                    replacements['timezone_offset'] = clock_config['timezone_offset']

                    night_begin_opts = str()
                    night_begin_opts += "<option value='0' {}>12:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 0 else "")
                    night_begin_opts += "<option value='1' {}>1:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 1 else "")
                    night_begin_opts += "<option value='2' {}>2:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 2 else "")
                    night_begin_opts += "<option value='3' {}>3:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 3 else "")
                    night_begin_opts += "<option value='4' {}>4:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 4 else "")
                    night_begin_opts += "<option value='5' {}>5:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 5 else "")
                    night_begin_opts += "<option value='6' {}>6:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 6 else "")
                    night_begin_opts += "<option value='7' {}>7:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 7 else "")
                    night_begin_opts += "<option value='8' {}>8:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 8 else "")
                    night_begin_opts += "<option value='9' {}>9:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 9 else "")
                    night_begin_opts += "<option value='10' {}>10:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 10 else "")
                    night_begin_opts += "<option value='11' {}>11:00am</option>".format("selected" if clock_config['change_times']['night_begins'] == 11 else "")
                    night_begin_opts += "<option value='12' {}>12:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 12 else "")
                    night_begin_opts += "<option value='13' {}>1:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 13 else "")
                    night_begin_opts += "<option value='14' {}>2:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 14 else "")
                    night_begin_opts += "<option value='15' {}>3:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 15 else "")
                    night_begin_opts += "<option value='16' {}>4:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 16 else "")
                    night_begin_opts += "<option value='17' {}>5:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 17 else "")
                    night_begin_opts += "<option value='18' {}>6:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 18 else "")
                    night_begin_opts += "<option value='19' {}>7:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 19 else "")
                    night_begin_opts += "<option value='20' {}>8:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 20 else "")
                    night_begin_opts += "<option value='21' {}>9:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 21 else "")
                    night_begin_opts += "<option value='22' {}>10:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 22 else "")
                    night_begin_opts += "<option value='23' {}>11:00pm</option>".format("selected" if clock_config['change_times']['night_begins'] == 23 else "")

                    replacements['night_start_options'] = night_begin_opts

                    night_end_opts = str()
                    night_end_opts += "<option value='0' {}>12:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 0 else "")
                    night_end_opts += "<option value='1' {}>1:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 1 else "")
                    night_end_opts += "<option value='2' {}>2:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 2 else "")
                    night_end_opts += "<option value='3' {}>3:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 3 else "")
                    night_end_opts += "<option value='4' {}>4:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 4 else "")
                    night_end_opts += "<option value='5' {}>5:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 5 else "")
                    night_end_opts += "<option value='6' {}>6:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 6 else "")
                    night_end_opts += "<option value='7' {}>7:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 7 else "")
                    night_end_opts += "<option value='8' {}>8:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 8 else "")
                    night_end_opts += "<option value='9' {}>9:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 9 else "")
                    night_end_opts += "<option value='10' {}>10:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 10 else "")
                    night_end_opts += "<option value='11' {}>11:00am</option>".format("selected" if clock_config['change_times']['night_ends'] == 11 else "")
                    night_end_opts += "<option value='12' {}>12:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 12 else "")
                    night_end_opts += "<option value='13' {}>1:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 13 else "")
                    night_end_opts += "<option value='14' {}>2:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 14 else "")
                    night_end_opts += "<option value='15' {}>3:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 15 else "")
                    night_end_opts += "<option value='16' {}>4:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 16 else "")
                    night_end_opts += "<option value='17' {}>5:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 17 else "")
                    night_end_opts += "<option value='18' {}>6:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 18 else "")
                    night_end_opts += "<option value='19' {}>7:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 19 else "")
                    night_end_opts += "<option value='20' {}>8:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 20 else "")
                    night_end_opts += "<option value='21' {}>9:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 21 else "")
                    night_end_opts += "<option value='22' {}>10:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 22 else "")
                    night_end_opts += "<option value='23' {}>11:00pm</option>".format("selected" if clock_config['change_times']['night_ends'] == 23 else "")

                    replacements['night_end_options'] = night_end_opts

                    replacements['day_foreground'] = rgb_triplet_to_hex(clock_config['theme']['day']['on'])
                    replacements['day_background'] = rgb_triplet_to_hex(clock_config['theme']['day']['off'])
                    replacements['night_foreground'] = rgb_triplet_to_hex(clock_config['theme']['night']['on'])
                    replacements['night_background'] = rgb_triplet_to_hex(clock_config['theme']['night']['off'])

                    replacements['fade_steps'] = clock_config['fade_steps']

                    response = response.format(**replacements)

                    print('  Sent clock_settings.html')

                    await writer.awrite(response)

            except Exception as reason:
                print(reason)

    # Close the socket
    await writer.aclose()

async def connect_and_serve():
    try:
        wifi_settings = await load_wifi_settings()
        wlan = await connect_to_wifi(wifi_settings)

        loop = asyncio.get_event_loop()
        server = asyncio.start_server(handle_http_connection, "0.0.0.0", 80)
        loop.create_task(server)

        loop.run_forever()

    except Exception as reason:
        print(reason)
        raise reason

def start():
    try:
        asyncio.run(connect_and_serve())

    finally:
        print('Dropped out of start')
        asyncio.new_event_loop()
