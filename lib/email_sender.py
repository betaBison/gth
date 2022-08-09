#!/usr/bin/env python3
#######################################################################
# Author(s):    Google, D. Knowles
# Date:         01 Dec 2020
# Desc:         Sends emails with updates on analytics
#######################################################################

import sys
import json
import pickle
import base64
import os.path
import configparser
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from apiclient import errors
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

if __name__ == "__main__":
    from plotter import Plotter
else:
    from lib.plotter import Plotter

class EmailSender():
    def __init__(self,config,prefix,verbose=False):
        """email sender initialization

        Parameters
        ----------
        config : configparser file
            configuration file
        prefix : string
            name for log file
        verbose : bool
            print verbose debugging statements

        """
        self.verbose = verbose
        self.receiver = config["emailsender"]["receiver"]

        # funky method but it works regardless of whether you're running
        # this file or the main.py file
        file_dir = os.path.dirname(os.path.realpath(__file__))
        # create some file paths
        self.token_path = file_dir + "/../config/email_token.pickle"
        self.cred_path = file_dir + "/../config/credentials.json"
        self.an_path = os.path.join(file_dir,"..","log",prefix,"analytics")

        # build service
        self.service = self.build_service()

        self.plotter = Plotter(prefix)

    def run(self):
        """main run function for the email sender

        """
        if self.verbose:
            print("beginning email sender...")

        # get all current analytics folders
        an_dirs = [content for content in os.listdir(self.an_path)
                   if os.path.isdir(os.path.join(self.an_path,content))]

        # sort by date
        an_dirs = sorted(an_dirs)

        if len(an_dirs) == 0:
            print("no analytics folders," \
                  + " please run analytics first")
            sys.exit(1)
        elif len(an_dirs) == 1:
            self.date_prev = None
        else:
            self.date_prev = an_dirs[-2]
        # get the date for the analytics folder and path to it
        self.date_cur = an_dirs[-1]
        self.an_dir = os.path.join(self.an_path,an_dirs[-1])

        # prep the attachments to be added to the message
        if self.verbose:
            print("creating email plots")
        self.prep_attachments()

        # prep the html message
        message_html = self.build_html_message()

        # create message with attachment
        if self.verbose:
            print("creating email message")
        message = self.create_mixed_message(message_html)

        # send the message
        self.send_message(self.service, "me", message)
        if self.verbose:
            print("...finished email sender. email message sent")

    def build_service(self):
        """builds gmail api service.

        Code copied with minor edits from
        https://developers.google.com/gmail/api/quickstart/python

        Returns
        -------
        service : gmail api
            gmail api service

        """

        # only need the scope to send emails
        SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

        creds = None
        # The file email_token.pickle stores the user's access and
        # refresh tokens, and is created automatically when the
        # authorization flow completes for the first time.
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available,
        # let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.cred_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        # build the service with the given credentials
        service = build("gmail", "v1", credentials=creds)

        return service

    def build_html_message(self):
        """Build HTML message

        create the bulk of the html message by combing lots of strings
        together that include tracked analytics and plots that were
        created

        Returns
        -------
        msg : string
            long string that contains the html message

        """
        # read in the analytics text data
        with open(os.path.join(self.an_dir,self.date_cur + ".json")) as f:
            data = json.load(f)

        began_tracking = data["began_tracking"]
        ended_tracking = data["ended_tracking"]
        stars_change = data["stars_change"]
        forks_change = data["forks_change"]

        # start this bulky string message
        msg = "<div>" + \
        "<font size='4'>" + \
        "This is your GTH (GitHub traffic history) update for the "
        if self.date_prev:
            msg += "dates " + self.date_prev + " to " + \
                   self.date_cur + ". "
        else:
            msg += "date " + self.date_cur + ". "
        msg += "Let's check out what happend. <br/><br/>"

        # include info about beginning and stopping tracking
        if len(began_tracking) == 0 and len(ended_tracking) == 0:
            msg += "Looks like there was no change of which " + \
            "repositories GTH is tracking (GTH did not start or " + \
            "stop tracking any repositories).<br/><br/>"
        else:
            if len(began_tracking) > 0:
                msg += "During this period, GTH began tracking the " + \
                "following repositories: <br/>"
                for repo in began_tracking:
                    msg += repo + "<br/>"
                msg += "<br/>"

            if len(ended_tracking) > 0:
                msg += "During this period, GTH stopped tracking " + \
                "the following repositories: <br/>"
                for repo in ended_tracking:
                    msg += repo + "<br/>"
                msg += "<br/>"

        # include data about stars and forks
        if len(stars_change) == 0 and len(forks_change) == 0:
            msg += "Looks like there was no change in the " + \
            "star count or fork count for any of your respositories "+ \
            " during this period.<br/><br/>"
        else:
            if len(stars_change) > 0:
                msg += "During this period, these repositories had " + \
                "the following star count changes: <br/>"
                for change in stars_change:
                    msg += change[0] + " : " + change[1] + "<br/>"
                msg += "<br/>"

            if len(forks_change) > 0:
                msg += "During this period, these repositories " + \
                "changed their fork counts: <br/>"
                for change in forks_change:
                    msg += change[0] + " : " + change[1] + "<br/>"
                msg += "<br/>"

        # include some graphs for visualization
        msg += "Let's graph out some of the highlights of your " + \
        "repositories during this period! Here's your clone " + \
        "history for your top repositories during this period: <br/>"

        msg += "<img src='cid:" + self.fig_names[0] +"'/> <br/> "
        msg += "<br/>"
        msg += "<img src='cid:" + self.fig_names[2] +"'/> <br/> "

        msg += "<br/><br/>"

        msg += "And this is the view traffic for your top " + \
        "repositories: <br/>"

        msg += "<img src='cid:" + self.fig_names[1] +"'/> <br/> "
        msg += "<br/>"
        msg += "<img src='cid:" + self.fig_names[3] +"'/> <br/> "

        msg += "<br/><br/>"

        msg += "And finally, let's see how far your repositories " + \
        "have come. Check out the cumulative views your top " + \
        "repositories have managed to snag during the entire time " + \
        "history that you have been using GTH. Wow! <br/>"

        msg += "<img src='cid:" + self.fig_names[4] +"'/> <br/> "
        msg += "<br/><br/></font></div>"

        # add a simple disclaimer
        msg += "<div><font size='2'> To unsubscribe, please contact "+ \
        "the sender of this email and request that they stop " + \
        "sending you emails. For more information, please see "+ \
        "https://github.com/betaBison/gth."

        msg += "</font></div>"

        return msg

    def prep_attachments(self):
        """Prepare attachements.

        call the plotter function and correlate figure names with
        the figures that were created

        """
        self.fig_paths = self.plotter.create_email_plots(self.date_cur,
                                                         self.date_prev)
        self.fig_names = ["clones_daily","views_daily",
                          "clones_unique","views_unique",
                          "views_history"]

    def create_mixed_message(self, message_html):
        """Create a message for an email.

        Copied with edits from
        https://developers.google.com/gmail/api/guides/sending
        Also see this answer for how to add attachments
        https://stackoverflow.com/questions/1633109/

        Parameters
        ----------
        message_html : string
            html text message to be sent

        Returns
        -------
        msg_object : base64url encoded email object
            email object

        """

        # update the receiver and the subject
        to = self.receiver
        if self.date_prev:
            subject = "GTH Update for " + self.date_prev + \
                      " to " + self.date_cur
        else:
            subject = "GTH Update for " + self.date_cur

        message = MIMEMultipart("mixed")
        message["to"] = to
        # the sender is commented out on purpose. Including the sender
        # field will tag emails sent as dangerous. If you let the api
        # figure out the sender then it won't flag the emails.
        # message["from"] = this is not included on purpose.
        message["subject"] = subject

        html_part = MIMEMultipart("related")

        body = MIMEText(message_html,"html")
        html_part.attach(body)

        # attach each figure that is provided
        for i,attachment in enumerate(self.fig_paths):
            img_data = open(attachment,"rb").read()
            img = MIMEImage(img_data,attachment[-3:])
            # link figure with its corresponding name
            # that angle brackets are important here!
            img.add_header("Content-Id", "<"+self.fig_names[i]+">")
            img.add_header("Content-Disposition", "inline",
                           filename=attachment)
            html_part.attach(img)

        message.attach(html_part)

        return {"raw": base64.urlsafe_b64encode(
            message.as_string().encode("utf-8")).decode("utf-8")}

    def send_message(self, service, user_id, message):
        """Send an email message.

        Copied with minor edits from
        https://developers.google.com/gmail/api/guides/sending

        Parameters
        ----------

        service : Gmail API service instance
            Authorized Gmail API
        user_id : string
            User's email address. The special value
            of "me" can be used to indicate the authenticated user.
        message : string
            Message to be sent.

        Returns
        -------
        message : message object
            the sent message
        """

        try:
            message = (service.users().messages().send(userId=user_id,
                       body=message).execute())
            # print("Message Id: %s" % message["id"])
            return message
        except errors.HttpError as error:
            print("An error occurred: %s" % error)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    # funky method but it works regardless of whether you're running
    # this file or the main.py file
    file_dir = os.path.dirname(os.path.realpath(__file__))
    config.read(file_dir + "/../config/settings_standard.ini")

    es = EmailSender(config,"settings_standard",True)
    es.run()
