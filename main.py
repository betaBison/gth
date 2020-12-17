#!/usr/bin/env python3
#######################################################################
# Author(s):    D. Knowles
# Date:         30 Aug 2019
# Desc:         Github Traffic Tool
#######################################################################

import os
import configparser

import lib.plotter as libplotter
from lib.analytics import Analytics
from lib.email_sender import EmailSender
from lib.traffic_requester import TrafficRequester

def main():
    # main options
    save_plots = True
    verbose = True

    # read configuration file
    config = configparser.ConfigParser()
    file_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = file_dir + "/config/settings.ini"
    config.read(config_path)

    # create instance of traffic requester
    tr = TrafficRequester(config,verbose)

    # run traffic requester
    tr.run()

    # create instance of analytics
    an = Analytics(verbose)

    # run analytics
    an.run()

    # create instance of email sender
    es = EmailSender(config,verbose)

    # send email
    es.run()

    # create and show plots if requested
    if save_plots:
        # create a bunch of plots as desired
        libplotter.create_plots(verbose)


if __name__ == "__main__":
    main()
