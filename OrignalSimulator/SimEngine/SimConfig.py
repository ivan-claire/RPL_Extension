#!/usr/bin/python
"""
\brief Holds the overall configuration of a simulation.

Configuration is read from a configuration file, and accessible in dotted
notation:

   simconfig.execution.numCores

This configuration contains the different steps of a simulation, including
what gets called after the simulation is done.
A single configuration turns into multiple SimSettings, for each combination
of settings.

\author Thomas Watteyne <thomas.watteyne@inria.fr>
"""

# =========================== imports =========================================

import json
import glob
import os
import platform
import sys
import time

import SimSettings

# =========================== defines =========================================

# =========================== body ============================================

class DotableDict(dict):

    __getattr__= dict.__getitem__

    def __init__(self, d):
        self.update(**dict((k, self.parse(v))
                           for k, v in d.iteritems()))

    @classmethod
    def parse(cls, v):
        if isinstance(v, dict):
            return cls(v)
        elif isinstance(v, list):
            return [cls.parse(i) for i in v]
        else:
            return v

class SimConfig(dict):

    # class variables, which are shared among all the instances
    _startTime          = None
    _log_directory_name = None

    def __init__(self, configfile=None, configdata=None):

        if SimConfig._startTime is None:
            # startTime needs to be initialized
            SimConfig._startTime = time.time()

        if   configfile is not None:
            # store params
            self.configfile = configfile

            # read config file
            if configfile == '-':
                # read config.json from stdin
                self._raw_data = sys.stdin.read()
            else:
                with open(self.configfile, 'r') as file:
                    self._raw_data = file.read()
        elif configdata is not None:
            self._raw_data = configdata
        else:
            raise Exception()

        # store config
        self.config   = DotableDict(json.loads(self._raw_data))

        # decide a directory name for log files
        if SimConfig._log_directory_name is None:
            self._decide_log_directory_name()

    def __getattr__(self, name):
        return getattr(self.config, name)

    def get_config_data(self):
        return self._raw_data

    def get_log_directory_name(self):
        return SimConfig._log_directory_name

    @classmethod
    def get_startTime(cls):
        return cls._startTime

    @staticmethod
    def generate_config(settings_dict, random_seed):
        regular_field = settings_dict
        # remove cpuID, run_id, log_directory, and combinationKeys, which
        # shouldn't be in the regular field
        del regular_field['cpuID']
        del regular_field['run_id']
        del regular_field['logDirectory']
        del regular_field['combinationKeys']
        # put random seed
        regular_field['exec_randomSeed'] = random_seed

        # save exec_numMotes value and remove 'exec_numMotes' from
        # regular_field
        exec_numMote = regular_field['exec_numMotes']
        del regular_field['exec_numMotes']

        config_json = {
            'settings': {
                'combination': {'exec_numMotes': [exec_numMote]},
                'regular': regular_field
            }
        }
        config_json['version'] = 0
        config_json['post'] = []
        config_json['log_directory_name'] = 'startTime'
        config_json['logging'] = 'all'
        config_json['execution'] = {
            'numCPUs': 1,
            'numRuns': 1
        }
        return config_json

    def _decide_log_directory_name(self):

        assert SimConfig._log_directory_name is None

        # determine log_directory_name
        if   self.log_directory_name == 'startTime':
            log_directory_name = '{0}-{1:03d}'.format(
                time.strftime(
                    "%Y%m%d-%H%M%S",
                    time.localtime(int(SimConfig._startTime))
                ),
                int(round(SimConfig._startTime * 1000)) % 1000
            )
        elif self.log_directory_name == 'hostname':
            # hostname is stored in platform.uname()[1]
            hostname = platform.uname()[1]
            log_directory_path = os.path.join(
                SimSettings.SimSettings.LOG_ROOT_DIR,
                hostname
            )
            # add suffix if there is a directory having the same hostname
            if os.path.exists(log_directory_path):
                index = len(glob.glob(log_directory_path + '*'))
                log_directory_name = '_'.join((hostname, str(index)))
            else:
                log_directory_name = hostname
        else:
            raise NotImplementedError(
                'log_directory_name "{0}" is not supported'.format(
                    self.log_directory_name
                )
            )

        SimConfig._log_directory_name = log_directory_name
