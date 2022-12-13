#!/usr/bin/env python3

import logging


class CustomLogger(object):
    """
    A logger class
    """
    def __init__(self, name, loglevel=logging.INFO):
        self.loglevel = loglevel
        self.name = name

    def getlogger(self):
        """
        Logging setup
        :return logger:
        """
        # logger
        logger = logging.getLogger()
        logger.setLevel(self.loglevel)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(self.loglevel)
        # create formatter
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - [%(funcName)s] -  %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        logger.addHandler(ch)
        logger.propagate = False
        return logger
