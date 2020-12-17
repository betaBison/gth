#!/usr/bin/env python3
#######################################################################
# Author(s):    D. Knowles
# Date:         30 Nov 2020
# Desc:         Github traffic history requester
#######################################################################

import os
import sys
import datetime
import configparser
import pandas as pd
from github import Github

class TrafficRequester():
    def __init__(self,config,verbose=False):
        """
        Desc:
            traffic requester initialization
        Input(s):
            config (configparser file) : configuration file
            verbose (bool) : print verbose debugging statements
        Output(s):
            None
        """

        self.verbose = verbose              # lots of print statements
        self.config = config                # config file

        # authorization code from github oauth
        oauth_token = self.config["authorization"]["oauth"]

        # number of previous days for which to get view and clone data
        # default (and max) is 14. Changing to a lower number will
        # marginally speed process time but isn't recommended.
        self.dtp = 14

        self.g = Github(oauth_token)        # create Github instance

        self.user = self.g.get_user().login # define oauth owner

        self.repo_objects = []              # list of repositories

        self.df = pd.DataFrame()            # dateframe to store date


    def run(self):
        """
        Desc:
            main run function for traffic requester
        Input(s):
            None
        Output(s):
            None
        """

        if self.verbose:
            print("beginning traffic requester...")

        # get latest list of owned repositories and repos contributed to
        self.get_repositories()

        # request some data from github
        if self.verbose:
            print("beginning to request data for each repoistory")
        self.get_history()

        # log raw data
        if self.verbose:
            print("logging raw data")
        self.log_data()

        if self.verbose:
            print("...finished traffic requester")

    def get_repositories(self):
        """
        Desc:
            checks which repositories are owned by the user or to which
            the user has contributed. Adds all of these repo names to
            the dataframe.
        Input(s):
            None
        Output(s):
            None
        """
        repo_names = []

        owner_count = 0
        contributor_count = 0

        for repo in self.g.get_user().get_repos("all"):
            if repo.owner.login == self.user:
                self.repo_objects.append(repo)
                repo_names.append(repo.full_name)
                owner_count += 1
            else:
                for contributor in repo.get_contributors():
                    if contributor.login == self.user:
                        self.repo_objects.append(repo)
                        repo_names.append(repo.full_name)
                        contributor_count += 1
        self.df["repo"] = repo_names
        if self.verbose:
            print("found ",owner_count," owned repositories")
            print("found ",contributor_count, "contributor repositories")

    def get_history(self):
        """
        Desc:
            requests traffic history for each repository and adds all
            information to the dataframe
        Input(s):
            None
        Output(s):
            None
        """
        stargazers = []
        forks = []
        clones_2weeks = []
        clones_uniques_2weeks = []
        views_2weeks = []
        views_uniques_2weeks = []
        referrers_top_10 = []
        content_top_10 = []

        # github works in UTC+0 timezone no matter where you are,
        # so get UTC+0 date and the previous days
        date = datetime.datetime.utcnow().date()
        last_dates = []
        for dd in range(self.dtp):
            date = date - datetime.timedelta(days=1)
            last_dates.append(date)
        last_dates.reverse()

        # initialize daily view and clone count to dictionary of zeros
        # note that [{}]*listsize fails because it creates a list of
        # pointers all to the same dictionary
        clones_daily = list({str(last_dates[dd]): 0
                         for dd in range(self.dtp)}
                         for i in range(len(self.repo_objects)))
        clones_uniques_daily = list({str(last_dates[dd]): 0
                                 for dd in range(self.dtp)}
                                 for i in range(len(self.repo_objects)))
        views_daily = list({str(last_dates[dd]): 0
                        for dd in range(self.dtp)}
                        for i in range(len(self.repo_objects)))
        views_uniques_daily = list({str(last_dates[dd]): 0
                                for dd in range(self.dtp)}
                                for i in range(len(self.repo_objects)))

        for rr,repo in enumerate(self.repo_objects):
            if self.verbose:
                print("requesting data for repository ",
                       rr+1,"/",len(self.repo_objects))
            # append stars and forks
            stargazers.append(repo.stargazers_count)
            forks.append(repo.forks_count)

            # append clones data
            clones_2weeks.append(repo.get_clones_traffic()["count"])
            clones_uniques_2weeks.append(repo.get_clones_traffic()["uniques"])
            for clone in repo.get_clones_traffic()["clones"]:
                if clone.timestamp.date() in last_dates:
                    clones_daily[rr][str(clone.timestamp.date())] = clone.count
                    clones_uniques_daily[rr][str(clone.timestamp.date())] = clone.uniques

            # append views data
            views_2weeks.append(repo.get_views_traffic()["count"])
            views_uniques_2weeks.append(repo.get_views_traffic()["uniques"])
            for view in repo.get_views_traffic()["views"]:
                if view.timestamp.date() in last_dates:
                    views_daily[rr][str(view.timestamp.date())] = view.count
                    views_uniques_daily[rr][str(view.timestamp.date())] = view.uniques

            # append referrers and top paths
            referrers_top_10.append(repo.get_top_referrers())
            content_top_10.append(repo.get_top_paths())

        self.df["stars"] = stargazers
        self.df["forks"] = forks
        self.df["clones_2weeks"] = clones_2weeks
        self.df["clones_uniques_2weeks"] = clones_uniques_2weeks
        self.df["views_2weeks"] = views_2weeks
        self.df["views_uniques_2weeks"] = views_uniques_2weeks
        self.df["clones_daily"] = clones_daily
        self.df["clones_uniques_daily"] = clones_uniques_daily
        self.df["views_daily"] = views_daily
        self.df["views_uniques_daily"] = views_uniques_daily
        self.df["referrers_top_10"] = referrers_top_10
        self.df["content_top_10"] = content_top_10

    def log_data(self):
        """
        Desc:
            save raw data to log file
        Input(s):
            None
        Output(s):
            None
        """
        # funky method but it works regardless of whether you're running
        # this file or the main.py file
        file_dir = os.path.dirname(os.path.realpath(__file__))
        log_dir = file_dir + "/../log/"
        raw_dir = log_dir + "raw/"

        # create log directory if it doesn't yet exist
        if not os.path.isdir(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print("e: ",e)
                sys.exit(1)

        # create raw data directory if it doesn't yet exist
        if not os.path.isdir(raw_dir):
            try:
                os.makedirs(raw_dir)
            except OSError as e:
                print("e: ",e)
                sys.exit(1)

        # record raw data as date of last saved information
        date_today = datetime.datetime.utcnow().date()
        last_date = date_today - datetime.timedelta(days=1)
        last_date = str(last_date)
        self.df.to_csv(raw_dir + last_date + ".csv",index=False)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    # funky method but it works regardless of whether you're running
    # this file or the main.py file
    file_dir = os.path.dirname(os.path.realpath(__file__))
    config.read(file_dir + "/../config/settings.ini")

    tr = TrafficRequester(config,True)
    tr.run()
