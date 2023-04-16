#!/usr/bin/env python
# Python script om P1 telegram weer te geven
# Originele script: http://domoticx.com/p1-poort-slimme-meter-data-naar-node-red-mqtt/
# Toelichting telegram velden: http://domoticx.com/p1-poort-slimme-meter-hardware/
# Toegevoegd op 27-03-2022: try except handling

import os
import datetime
import time    
import re
import serial
import paho.mqtt.client as paho

broker="192.168.178.65"
port=1883

def on_publish(client,userdata,result): #create function for callback
  print("data published")
  pass

client1=paho.Client("control1") #create client object
client1.on_publish = on_publish #assign function to callback
client1.connect(broker,port) #establish connection

# Seriele poort confguratie
ser = serial.Serial()

# DSMR 2.2 > 9600 7E1:
ser.baudrate = 9600
ser.bytesize = serial.SEVENBITS
ser.parity = serial.PARITY_EVEN
ser.stopbits = serial.STOPBITS_ONE

# DSMR 4.0/4.2 > 115200 8N1:
#ser.baudrate = 115200
#ser.bytesize = serial.EIGHTBITS
#ser.parity = serial.PARITY_NONE
#ser.stopbits = serial.STOPBITS_ONE

ser.xonxoff = 0
ser.rtscts = 0
ser.timeout = 12
ser.port = "/dev/ttyUSB0"
ser.close()

while True:
    try:
        ser.open()
        checksum_found = False
        gasflag = 0

        while not checksum_found:
            telegram_line = ser.readline() # Lees een seriele lijn in.
            telegram_line = telegram_line.decode('ascii').strip() # Strip spaties en blanke regels

            # print (telegram_line)
            if re.match(b'(?=1-0:1.7.0)', telegram_line): #1-0:1.7.0 = Actueel verbruik in kW
                currentUsedKW = telegram_line[10:-4] # Knip het kW gedeelte eruit
                currentUsed = float(currentUsedKW) * 1000 # vermengvuldig met 1000 voor conversie naar Watt

            if re.match(b'(?=1-0:2.7.0)', telegram_line): #1-0:2.7.0 = Actueel opbrengst in kW
                currentGeneratedKW = telegram_line[10:-4] 
                currentGenerated = float(currentGeneratedKW) * 1000

            if re.match(b'(?=1-0:1.8.1)', telegram_line): #1-0:1.8.1 - Hoog tarief verbruikt
                sumUsedNight = float(telegram_line[10:-5])

            if re.match(b'(?=1-0:1.8.2)', telegram_line): #1-0:1.8.2 - Laag tarief verbruikt
                sumUsedDay = float(telegram_line[10:-5])

            if re.match(b'(?=1-0:2.8.1)', telegram_line): #1-0:2.8.1 - Hoog tarief geleverd
                sumGeneratedNight = float(telegram_line[10:-5])

            if re.match(b'(?=1-0:2.8.2)', telegram_line): #1-0:2.8.2 - Laag tarief geleverd
                sumGeneratedDay = float(telegram_line[10:-5])

            if gasflag == 1:
                gas = float(telegram_line[1:-1])
                gasflag = 0
   
            if re.match(b'(?=0-1:24.3.0)', telegram_line): #0-1:24.3.0 - Gasverbruik
                gasflag = 1

            # Check wanneer het uitroepteken ontavangen wordt (einde telegram)
            if re.match(b'(?=!)', telegram_line):
                checksum_found = True

        ser.close()

        ######################################
        # MQTT PUBLISH
        ######################################
        client1.publish("smart_meter/electricity/sum/used1", sumUsedNight)
        client1.publish("smart_meter/electricity/sum/used2", sumUsedDay)
        client1.publish("smart_meter/electricity/sum/generated1", sumGeneratedNight)
        client1.publish("smart_meter/electricity/sum/generated2", sumGeneratedDay)
        client1.publish("smart_meter/electricity/current/used", currentUsed)
        client1.publish("smart_meter/electricity/current/generated", currentGenerated)
        client1.publish("smart_meter/gas/sum", gas)
        client1.publish("smart_meter/timestamp", float(time.time()) * 1000)
        print(float(time.time()) * 1000)

    except:
        print('error')
        ser.close()
        client1.publish("smart_meter/error", "an error occured, please restart")
        os.system("python /home/pi/slimme_meter/slimme_meter_uitlezen.py")

