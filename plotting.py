import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates
import numpy as np
import bme680
import time
from datetime import datetime
import smtplib
import email
import ssl
import os
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

chktime = 0

#Sends an email based on the last 30 data points, a subject line, and a diagnostic package (if there is a value warning)
def send_email_figure(data_dict, flag_pkg, subject):
    global chktime
    port = 465
    smtp_server = "smtp.gmail.com"
    send_addr = "csucs370project@gmail.com"
    rec_addr = "csucs370project@gmail.com"
    password = "colostate370!"
    body = ""
    if flag_pkg != 0:
        body += """\
        Alert! The following parameters are outside their determined safe range:
        """
        for key in flag_pkg.keys():
            body += "{}: Recorded at {}\n".format(key.capitalize(), flag_pkg[key])
        body += """\
        Please consult the included data and figures to diagnose the issue.
        
        """
    else:
        body += "Semi-Hourly Environmental Diagnostic Report"
    for sect in data_dict.keys():
        body += """\
        {}
        minimum: {}
        maximum: {}
        average: {}
        
        """.format(sect.capitalize(), data_dict[sect][0], data_dict[sect][1], data_dict[sect][2])

    body += """\
    
    The CS370 "Lotus" Team:
    Jason Kiehlbauch
    Cole Riechert
    Matthew Clark"""

    msg = MIMEMultipart()
    msg["From"] = send_addr
    msg["To"] = rec_addr
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    for figure_name in data_dict.keys():
        img_data = open('{}.png'.format(figure_name), 'rb').read()
        image = MIMEImage(img_data, name=os.path.basename('{}.png'.format(figure_name)))
        msg.attach(image)

    # Log in to server using secure context and send email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(send_addr, password)
        server.sendmail(send_addr, rec_addr, msg.as_string())
        print("Email sent successfully! Check your inbox.")
        process_time = (datetime.now() - chktime).total_seconds()
        print("Process time from notification to email send: {} seconds".format(process_time))


#The main method - checks in a while(True) loop to see if time has changed and adds data point, then sends email

current_min = ""
values = {}
times = []

while True:
    try:
        sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
    except IOError:
        sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

    sensor.set_humidity_oversample(bme680.OS_2X)
    sensor.set_pressure_oversample(bme680.OS_4X)
    sensor.set_temperature_oversample(bme680.OS_8X)
    sensor.set_filter(bme680.FILTER_SIZE_3)
    sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

    tempflag = False
    humflag = False
    now = datetime.now()
    min_t = datetime.strftime(now, "%M")
    if min_t != current_min:
        current_min = min_t
        times.append(now)

        for name in dir(sensor.data):
            value = getattr(sensor.data, name)

            if name == 'temperature' or name == 'humidity':
                try:
                    values[name].append(value)
                    if len(values[name]) >= 60:
                        values[name].pop(0)
                except KeyError:
                    values[name] = []
                    values[name].append(value)
                    if len(values[name]) >= 60:
                        values[name].pop(0)

        print("Values added for {}".format(time.strftime("%I:%M%p")))

        if sensor.data.temperature > 30 or sensor.data.temperature < 20:
            tempflag = True
        if sensor.data.humidity > 40 or sensor.data.humidity < 20:
            humflag = True
        if tempflag or humflag:
            chktime = datetime.now()
            flag_pkg = {}
            if tempflag:
                print("WARNING: temperature out of range!")
                flag_pkg['temperature'] = sensor.data.temperature
            if humflag:
                print("WARNING: humidity out of range!")
                flag_pkg['humidity'] = sensor.data.humidity

            times_plot = matplotlib.dates.date2num(times)
            data_dict = {}

            for key in values.keys():
                # create the data dictionary to pass to the email function
                data_dict[key] = []
                data_dict[key].append(min(values[key]))
                data_dict[key].append(max(values[key]))
                data_dict[key].append(statistics.mean(values[key]))

                n = len(values[key])
                m = len(times_plot)
                plt.figure()
                plt.style.use('seaborn-whitegrid')
                plt.plot_date(times_plot[m-30:m], values[key][n-30:n], xdate=True, linestyle='solid')
                plot_title = key.capitalize() + " vs. Time"
                plt.title(plot_title)
                plt.xlabel("Time (XX:XX)")
                plt.ylabel(key)
                plt.gcf().autofmt_xdate()
                plt.savefig('{}.png'.format(key))
                plt.close()

            send_email_figure(data_dict, flag_pkg, "Environmental Warning Report")

        if current_min == "00" or current_min == "30":
            chktime = datetime.now()
            times_plot = matplotlib.dates.date2num(times)
            data_dict = {}

            for key in values.keys():
                #create the data dictionary to pass to the email function
                data_dict[key] = []
                data_dict[key].append(min(values[key]))
                data_dict[key].append(max(values[key]))
                data_dict[key].append(statistics.mean(values[key]))

                n = len(values[key])
                m = len(times_plot)
                plt.figure()
                plt.style.use('seaborn-whitegrid')
                plt.plot_date(times_plot[m - 30:m], values[key][n - 30:n], xdate=True, linestyle='solid')
                plot_title = key.capitalize() + " vs. Time"
                plt.title(plot_title)
                plt.xlabel("Time (XX:XX)")
                plt.ylabel(key)
                plt.gcf().autofmt_xdate()
                plt.savefig('{}.png'.format(key))
                plt.close()


            send_email_figure(data_dict, 0, "Semi-Hourly Report")


