import datetime
import board
import adafruit_dotstar as dotstar
import sys
import time
import json
import pytz

# Configure the LEDs
num_dots = 121
dots = dotstar.DotStar(board.SCK, board.MOSI, num_dots, brightness=0.9, auto_write=False)

# Set up the locations of the words on the LED strip
c = {
  "its": [118,121],
  "five": [100,104],
  "ten": [105,108],
  "quarter": [89,96],
  "twenty": [111,117],
  "half": [77,81],
  "past": [84,88],
  "until": [72,77],
  "to": [82,84],
  "oclock": [0,6],
  "hour_twelve": [22,28],
  "hour_one": [49,52],
  "hour_two": [51,54],
  "hour_three": [56,61],
  "hour_four": [7,11],
  "hour_five": [34,38],
  "hour_six": [12,15],
  "hour_seven": [61,66],
  "hour_eight": [45,50],
  "hour_nine": [29,33],
  "hour_ten": [15,18],
  "hour_eleven": [37,43],
  "hour_noon": [67,71],
  "night": [17,22],
}

# Initialize the previous state to everything off
last_state = []
for idx in range(121): last_state.append((0,0,0))

on = (175,175,175)
off = (0,0,0)

while True:
  # Load the config JSON file
  f = open('/home/pi/clock/config.json',)
  config = json.load(f)
  f.close()
   
  # We're alwasy showing "ITS"
  phrase = [c['its']]

  now = datetime.datetime.now(pytz.timezone(config['timezone']))
  hour = now.hour

  # Get minute as a decimal including the seconds
  minute = now.minute + now.second/60.0
  set_minute = False

  # Store the decimal hour to use for theme setting
  hour_with_minute = hour + minute/60.0

  # Build the phrases depending on the closest 5-minute division
  if   (minute >= 2.5 and minute < 7.5):   phrase.extend([c['five'], c['past']])
  elif (minute >= 7.5 and minute < 12.5):  phrase.extend([c['ten'], c['past']])
  elif (minute >= 12.5 and minute < 17.5): phrase.extend([c['quarter'], c['past']])
  elif (minute >= 17.5 and minute < 22.5): phrase.extend([c['twenty'], c['past']])
  elif (minute >= 22.5 and minute < 27.5): phrase.extend([c['twenty'], c['five'], c['past']])
  elif (minute >= 27.5 and minute < 32.5): phrase.extend([c['half'], c['past']])
  elif (minute >= 32.5 and minute < 37.5): phrase.extend([c['twenty'], c['five'], c['until']])
  elif (minute >= 37.5 and minute < 42.5): phrase.extend([c['twenty'], c['until']])
  elif (minute >= 42.5 and minute < 47.5): phrase.extend([c['quarter'], c['to']])
  elif (minute >= 47.5 and minute < 52.5): phrase.extend([c['ten'], c['to']])
  elif (minute >= 52.5 and minute < 57.5): phrase.extend([c['five'], c['until']])

  # If we weren't at the top of the hour, note that
  if (len(phrase) > 1): set_minute = True

  # If we're in the bottom of the hour, we're saying "until" so increment the hour
  if (minute >= 32.5): hour += 1

  # Wrap around at midnight
  if (hour == 24): hour = 0

  # Determine which word to show for the hour
  if (hour == 0):                  phrase.append(c['hour_twelve'])
  elif (hour == 1 or hour == 13):  phrase.append(c['hour_one'])
  elif (hour == 2 or hour == 14):  phrase.append(c['hour_two'])
  elif (hour == 3 or hour == 15):  phrase.append(c['hour_three'])
  elif (hour == 4 or hour == 16):  phrase.append(c['hour_four'])
  elif (hour == 5 or hour == 17):  phrase.append(c['hour_five'])
  elif (hour == 6 or hour == 18):  phrase.append(c['hour_six'])
  elif (hour == 7 or hour == 19):  phrase.append(c['hour_seven'])
  elif (hour == 8 or hour == 20):  phrase.append(c['hour_eight'])
  elif (hour == 9 or hour == 21):  phrase.append(c['hour_nine'])
  elif (hour == 10 or hour == 22): phrase.append(c['hour_ten'])
  elif (hour == 11 or hour == 23): phrase.append(c['hour_eleven'])
  elif (hour == 12):               phrase.append(c['hour_noon'])

  # If we're just showing the time and it's not noon, add the o'clock word to the phrase
  if (not set_minute and hour != 12): phrase.append(c['oclock'])

  # Set the color theme
  if (hour_with_minute >= config['change_times']['night_begins'] or
          hour_with_minute < config['change_times']['night_ends']):
        theme = 'night'
  else: theme = 'day'

  on = config['theme'][theme]['on']
  off = config['theme'][theme]['off']

  # Load the fade setting
  fade_steps = config['fade_steps']

  # Start determining the current state (initialized to everything off)
  state = []
  for dot in range(num_dots): state.append(off)

  # Loop through the words in the phrase and set the state of those LEDS to on
  for word in phrase:
    for dot in range(word[0], word[1]):
      state[dot] = on

  if (last_state != state):
    for step in range(fade_steps):
      fade = (step+1) / fade_steps

      # Assign the states to the actual LEDs
      for dot in range(num_dots):
        new_color = [0,0,0]

        for color in range(3):
          new_color[color] = int(last_state[dot][color] + fade * (state[dot][color] - last_state[dot][color]))

        dots[dot] = tuple(new_color)

      # We don't auto_write the LEDs, so now that we're ready, show the strip
      dots.show()

      time.sleep(0.05)

    # Save the last state
    last_state = state

  # Wait 10 seconds before running again
  time.sleep(10)
