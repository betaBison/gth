#!/usr/bin/env python3
#######################################################################
# Author(s):    D. Knowles
# Date:         30 Aug 2019
# Desc:         Github Traffic Tool
#######################################################################

import os
import configparser

from lib.plotter import Plotter
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
    config_path = file_dir + "/config/settings_standard.ini"
    prefix = "settings_standard"
    config.read(config_path)

    # create instance of traffic requester
    tr = TrafficRequester(config,prefix,verbose)

    # run traffic requester
    tr.run()

    # create instance of analytics
    an = Analytics(prefix,verbose)

    # run analytics
    an.run()

    # create instance of email sender
    es = EmailSender(config,prefix,verbose)

    # send email
    es.run()

    # create and show plots if requested
    if save_plots:
        pl = Plotter(prefix)
        # create a bunch of plots as desired
        pl.create_plots(verbose)


if __name__ == "__main__":
    main()
