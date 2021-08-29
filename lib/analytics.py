#!/usr/bin/env python3
#######################################################################
# Author(s):    D. Knowles
# Date:         03 Dec 2020
# Desc:         Traffic analytics
#######################################################################

import os
import sys
import ast
import json
import datetime
import pandas as pd
if __name__ == "__main__":
    import plotter as libplotter
else:
    import lib.plotter as libplotter


class Analytics():
    def __init__(self,verbose=False):
        """analytics initialization

        Parameters
        ----------
        verbose : bool
            print verbose debugging statements

        """
        self.verbose = verbose      # printing for debugging

        # funky method but it works regardless of whether you're running
        # this file or the main.py file
        file_dir = os.path.dirname(os.path.realpath(__file__))
        self.log_dir = file_dir + "/../log/"

        self.prev_exists = False    # exists a previous log to compare

    def run(self):
        """main run function for analytics

        """

        if self.verbose:
            print("beginning analytics...")

        # initialize empty analytics lists
        self.began_tracking = []    # new repos being tracked
        self.ended_tracking = []    # repos no longer being tracked
        self.stars_change = []      # change to stars count
        self.forks_change = []      # change to forks count

        # check directories and create if necessary
        analytics_needed = self.check_dirs()
        if len(analytics_needed) > 0:
            for raw_log in analytics_needed:
                if self.verbose:
                    print("analyzing raw log ",raw_log)

                # update current log being analyzed
                self.raw_log_current = raw_log

                # load log into dataframe
                self.load_log()

                # read in raw log to df and create repo dirs
                self.create_repo_dirs()

                # sort the raw data from the latest
                self.sort_raw_data()

            # check tracking changes
            self.check_tracking_change()

            if self.prev_exists:
                # update stars and forks
                self.check_stars_change()
                self.check_forks_change()

            # log raw data
            if self.verbose:
                print("logging analytics")
            self.log_analytics()

        # analytics_needed was empty
        else:
            if self.verbose:
                print("no analytics needed...")

        if self.verbose:
            print("...finished analytics")

    def check_dirs(self):
        """check and create directories

        create log directories if they don't yet exist and check
        which raw logs need to be analyzed.

        Returns
        -------
        analytics_needed : list
            the raw logs that do not yet have a corresponding analytics
            directory

        """

        raw_dir = self.log_dir + "raw/"
        an_dir = self.log_dir + "analytics/"

        if not os.path.isdir(raw_dir):
            print("no raw log directory," \
                  + " please run traffic requester first")
            sys.exit(1)

        # retrive the paths to all of the log files
        self.raw_logs = os.listdir(raw_dir)

        # sort by date
        self.raw_logs = sorted(self.raw_logs)

        if len(self.raw_logs) == 0:
            print("no raw log files," \
                  + " please run traffic requester first")
            sys.exit(1)

        # create analytics directory if it doesn't yet exist
        if not os.path.isdir(an_dir):
            try:
                os.makedirs(an_dir)
            except OSError as e:
                print("e: ",e)
                sys.exit(1)

        # get all current analytics folders
        an_dirs = [content for content in os.listdir(an_dir)
                   if os.path.isdir(os.path.join(an_dir,content))]

        # sort by date
        an_dirs = sorted(an_dirs)

        if len(an_dirs) == 0:
            # if no analytics have been calculated yet, then all of the
            # raw logs need to be analyzed
            analytics_needed = self.raw_logs.copy()
            # there's no previous log directory
            self.prev_exists = False
        else:
            # convert last analytics date to datetime
            last_date = datetime.datetime.strptime(an_dirs[-1],
                                                "%Y-%m-%d").date()
            # there exists a previous analytics directory
            self.prev_exists = True
            # retrieve the raw log from the last analytics
            prev_log_path = raw_dir + an_dirs[-1] + ".csv"
            self.prev_log_df = pd.read_csv(prev_log_path)

            analytics_needed = []
            # iterate through all of the log files
            for raw_log in self.raw_logs:
                raw_date = datetime.datetime.strptime(raw_log[:-4],
                                                    "%Y-%m-%d").date()
                # if the raw log date came after the last analytics,
                # then add it to the list of raw logs that need to be
                # analyzed
                if raw_date > last_date:
                    analytics_needed.append(raw_log)

        return analytics_needed

    def load_log(self):
        """load_log file into dataframe

        """
        raw_dir = self.log_dir + "raw/"

        self.log_df = pd.read_csv(raw_dir + self.raw_log_current)

    def create_repo_dirs(self):
        """create log directories if they don't yet exist

        """
        repos_dir = self.log_dir + "repos/"

        # create repos data directory if it doesn't yet exist
        if not os.path.isdir(repos_dir):
            try:
                os.makedirs(repos_dir)
            except OSError as e:
                print("e: ",e)
                sys.exit(1)

        # create individual repo directoroy if it doesn't yet exist
        for repo in self.log_df["repo"]:
            repo_dir = repos_dir + self.full2dir(repo) + "/"
            if not os.path.isdir(repo_dir):
                try:
                    os.makedirs(repo_dir)
                except OSError as e:
                    print("e: ",e)
                    sys.exit(1)

    def sort_raw_data(self):
        """Sort through each of the main metrics for each repository

        """

        # iterate over repository indexes
        for ri in self.log_df.index:

            self.update_nondaily_metric(ri,"stars")
            self.update_nondaily_metric(ri,"forks")
            self.update_nondaily_metric(ri,"clones_2weeks")
            self.update_nondaily_metric(ri,"clones_uniques_2weeks")
            self.update_nondaily_metric(ri,"views_2weeks")
            self.update_nondaily_metric(ri,"views_uniques_2weeks")

            self.update_daily_metric(ri,"clones_daily")
            self.update_daily_metric(ri,"clones_uniques_daily")
            self.update_daily_metric(ri,"views_daily")
            self.update_daily_metric(ri,"views_uniques_daily")

    def update_nondaily_metric(self,ri,col_name):
        """update nondaily metrics

        update metrics that are not daily, this function simply
        appends the newest value to the log file

        Parameters
        ----------
        ri : int
            row of dataframe to read from
        col_name : string
            column name and thus file name for the specific metric

        """
        repos_dir = self.log_dir + "repos/"
        repo_dir = repos_dir + self.full2dir(self.log_df["repo"][ri])
        file_path = repo_dir + "/" + col_name + ".csv"

        # the nondaily metrics just get added to their respective log
        if not os.path.exists(file_path):
            f = open(file_path,"w")
            f.write("date," + col_name + "\n")
        else:
            f = open(file_path,"a")
        f.write(self.raw_log_current[:-4] + "," + \
                str(self.log_df[col_name][ri]) + "\n")
        f.close()

    def update_daily_metric(self,ri,col_name):
        """update metrics that are daily

        this function reads through
        the old data and only adds new daily values

        Parameters
        ----------
        ri : int
            row of dataframe to read from
        col_name : string
            column name and thus file name for the specific metric

        """
        repos_dir = self.log_dir + "repos/"
        repo_dir = repos_dir + self.full2dir(self.log_df["repo"][ri])
        file_path = repo_dir + "/" + col_name + ".csv"

        # organize most current data
        data_cur_dict = ast.literal_eval(self.log_df[col_name][ri])
        # convert to list
        data_cur = list(data_cur_dict.items())
        # sort dictionary keys by date
        data_cur = sorted(data_cur,key=lambda x: x[0])

        if not os.path.exists(file_path):
            f = open(file_path,"w")
            f.write("date," + col_name + "\n")
            for row in data_cur:
                f.write(row[0] + "," + str(row[1]) + "\n")
        else:
            f = open(file_path,"a")

            # read in previous data
            data_prev = pd.read_csv(file_path)
            for row in data_cur:
                if row[0] not in data_prev["date"].values:
                    f.write(row[0] + "," + str(row[1]) + "\n")
        f.close()

    def full2dir(self,fullname):
        """changes full repository name into a directory name

        Parameters
        ----------
        fullname : string
            full repository name

        Returns
        -------
        dirname : string
            new directory name

        """

        # remove forward slash
        dirname = fullname.replace("/","-")

        # remove periods
        dirname = dirname.replace(".","")

        # remove spaces
        dirname = dirname.replace(" ","")

        return dirname

    def check_tracking_change(self):
        """check tracked repositories

        checks which repositories are beginning to be tracked or have
        stopped being tracked.

        """
        if self.prev_exists:
            # add repos no longer tracked to the list
            for repo in self.prev_log_df["repo"]:
                if repo not in self.log_df["repo"].values:
                    self.ended_tracking.append(repo)

            # add newly tracked repos to list
            for repo in self.log_df["repo"]:
                if repo not in self.prev_log_df["repo"].values:
                    self.began_tracking.append(repo)
        else:
            # if only a single log, then they're all new!
            for repo in self.log_df["repo"]:
                self.began_tracking.append(repo)

        if self.verbose:
            print("began tracking:\n",self.began_tracking)
            print("ended tracking:\n",self.ended_tracking)

    def check_stars_change(self):
        """Checks start counts

        checks whether the stars count has changed and appends any
        changes to self.stars_change

        """

        # iterate over repositories
        for repo in self.log_df["repo"]:
            # only valid if in both new and old dataframe
            if repo in self.prev_log_df["repo"].values:
                stars_cur = self.log_df.loc[self.log_df["repo"] == repo]["stars"].values[0]
                stars_prev = self.prev_log_df.loc[self.prev_log_df["repo"] == repo]["stars"].values[0]
                if stars_cur != stars_prev:
                    self.stars_change.append((repo,str(stars_cur-stars_prev)))

        if self.verbose:
            print("stars change:")
            for change in self.stars_change:
                print(change[0],": ",change[1])

    def check_forks_change(self):
        """Checks forks counts

        checks whether the forks count has changed and appends any
        changes to self.forks_change

        """

        # iterate over repositories
        for repo in self.log_df["repo"]:
            # only valid if in both new and old dataframe
            if repo in self.prev_log_df["repo"].values:
                forks_cur = self.log_df.loc[self.log_df["repo"] == repo]["forks"].values[0]
                forks_prev = self.prev_log_df.loc[self.prev_log_df["repo"] == repo]["forks"].values[0]
                if forks_cur != forks_prev:
                    self.forks_change.append((repo,str(forks_cur-forks_prev)))

        if self.verbose:
            print("forks change:")
            for change in self.forks_change:
                print(change[0],": ",change[1])

    def log_analytics(self):
        """Logs the analytics to a json file

        """
        an_dir = self.log_dir + "analytics/" + self.raw_log_current[:-4] + "/"

        # create analytics directory if it doesn't yet exist
        if not os.path.isdir(an_dir):
            try:
                os.makedirs(an_dir)
            except OSError as e:
                print("e: ",e)
                sys.exit(1)

        # create analytics dictionary
        analytics_dict = {"began_tracking":self.began_tracking,
                          "ended_tracking":self.ended_tracking,
                          "stars_change":self.stars_change,
                          "forks_change":self.forks_change}

        # write analytics dictionary to file
        json_data = json.dumps(analytics_dict)
        f = open(an_dir+self.raw_log_current[:-4]+".json","w")
        f.write(json_data)
        f.close()

if __name__ == "__main__":
    verbose = True

    an = Analytics(verbose)
    an.run()
