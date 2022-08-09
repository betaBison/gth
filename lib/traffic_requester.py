#!/usr/bin/env python3
#######################################################################
# Author(s):    D. Knowles
# Date:         30 Nov 2020
# Desc:         Github traffic history requester
#######################################################################

import os
import sys
import ast
import time
import datetime
import configparser
import pandas as pd
from github import Github

class TrafficRequester():
    def __init__(self, config, prefix="settings_standard", verbose=False):
        """traffic requester initialization

        Parameters
        ----------
        config : configparser file
            configuration file
        prefix : string
            name for log file
        verbose : bool
            print verbose debugging statements

        """

        self.verbose = verbose              # lots of print statements
        self.config = config                # config file
        self.prefix = prefix

        # authorization code from github oauth
        oauth_token = self.config["authorization"]["oauth"]

        # repository types to track
        self.repo_types = ast.literal_eval(self.config["traffic_requester"]["repo_types"])
        # conform to lower case just to be sure
        self.repo_types = [x.lower() for x in self.repo_types]

        # organizations to pull from
        self.repo_organizations = ast.literal_eval(self.config["traffic_requester"]["repo_organizations"])
        # conform to lower case just to be sure
        self.repo_organizations = [x.lower() for x in self.repo_organizations]



        # number of previous days for which to get view and clone data
        # default (and max) is 14. Changing to a lower number will
        # marginally speed process time but isn't recommended.
        self.dtp = 14

        self.g = Github(oauth_token)        # create Github instance

        self.user = self.g.get_user().login # define oauth owner

        self.repo_objects = []              # list of repositories

        self.df = pd.DataFrame()            # dateframe to store date


    def run(self):
        """main run function for traffic requester

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
        """api request for repositories

        checks which repositories are owned by the user or to which
        the user has contributed. Adds all of these repo names to
        the dataframe.

        """
        repo_names = []

        owner_count = 0
        contributor_count = 0

        for repo in self.g.get_user().get_repos("all"):
            if repo.full_name.split("/")[0].lower() not in self.repo_organizations and "all" not in self.repo_organizations:
                continue

            if "all" in self.repo_types:
                self.repo_objects.append(repo)
                repo_names.append(repo.full_name)
            elif "owner" in self.repo_types and repo.owner.login == self.user:
                self.repo_objects.append(repo)
                repo_names.append(repo.full_name)
                owner_count += 1
            elif "contributor" in self.repo_types:
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
        """requests traffic history for each repository

        Then adds all information to the dataframe

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

            data_obtained = False

            while not data_obtained:
                try:
                    # append stars and forks
                    stargazers_count = repo.stargazers_count
                    forks_count = repo.forks_count

                    # append clones data
                    clones_2weeks_data = repo.get_clones_traffic()["count"]
                    clones_uniques_2weeks_data = repo.get_clones_traffic()["uniques"]
                    clone_data = repo.get_clones_traffic()["clones"]


                    # append views data
                    views_2weeks_data = repo.get_views_traffic()["count"]
                    views_uniques_2weeks_data = repo.get_views_traffic()["uniques"]
                    view_data = repo.get_views_traffic()["views"]

                    # append referrers and top paths
                    referrers_top_10_data = repo.get_top_referrers()
                    content_top_10_data = repo.get_top_paths()
                    data_obtained = True
                except Exception as e:
                    print(e)
                    time.sleep(0.1)
                    print("attempting retry for",repo.full_name)

            # append to data if all requests were successful

            # append stars and forks
            stargazers.append(stargazers_count)
            forks.append(forks_count)

            # append clones data
            clones_2weeks.append(clones_2weeks_data)
            clones_uniques_2weeks.append(clones_uniques_2weeks_data)
            for clone in clone_data:
                if clone.timestamp.date() in last_dates:
                    clones_daily[rr][str(clone.timestamp.date())] = clone.count
                    clones_uniques_daily[rr][str(clone.timestamp.date())] = clone.uniques

            # append views data
            views_2weeks.append(views_2weeks_data)
            views_uniques_2weeks.append(views_uniques_2weeks_data)
            for view in view_data:
                if view.timestamp.date() in last_dates:
                    views_daily[rr][str(view.timestamp.date())] = view.count
                    views_uniques_daily[rr][str(view.timestamp.date())] = view.uniques

            # append referrers and top paths
            referrers_top_10.append(referrers_top_10_data)
            content_top_10.append(content_top_10_data)


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
        """save raw data to log file

        """
        # funky method but it works regardless of whether you're running
        # this file or the main.py file
        file_dir = os.path.dirname(os.path.realpath(__file__))
        log_dir = file_dir + "/../log/"
        prefix_dir = os.path.join(log_dir,self.prefix)
        raw_dir = os.path.join(prefix_dir,"raw")

        # create directories if they don't yet exist
        for dir in [log_dir, prefix_dir, raw_dir]:
            if not os.path.isdir(dir):
                try:
                    os.makedirs(dir)
                except OSError as e:
                    print("e: ",e)
                    sys.exit(1)

        # record raw data as date of last saved information
        date_today = datetime.datetime.utcnow().date()
        last_date = date_today - datetime.timedelta(days=1)
        last_date = str(last_date)
        self.df.to_csv(os.path.join(raw_dir,last_date + ".csv"),index=False)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    # funky method but it works regardless of whether you're running
    # this file or the main.py file
    file_dir = os.path.dirname(os.path.realpath(__file__))
    config.read(file_dir + "/../config/settings_standard.ini")

    tr = TrafficRequester(config,"settings_standard",True)
    tr.run()
