#!/bin/python3.11
"""
SlurmStack run script
"""

import argparse
from dotenv import load_dotenv
import os

import logging
import logging.config

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    load_dotenv()  # load variables from .env file to os.environ

    parser = argparse.ArgumentParser(description="slurmstack.py automates cluster node creation and role deployment. Parameters can be passed via command-line flags or defined in a .env file.")

    parser.add_argument("-c", "--cluster-name", default=os.environ.get("SS_CLUSTER_NAME"), required=not os.environ.get("SS_CLUSTER_NAME"))
    parser.add_argument("-n", "--nodes-count", type=int, default=os.environ.get("SS_NODES_COUNT"), required=not os.environ.get("SS_NODES_COUNT"))
    parser.add_argument("-nf", "--nodes-flavour", default=os.environ.get("SS_NODES_FLAVOUR"), required=not os.environ.get("SS_NODES_FLAVOUR"))
    parser.add_argument("-np", "--nodes-prefix", default=os.environ.get("SS_NODES_PREFIX"), required=not os.environ.get("SS_NODES_PREFIX"))
    parser.add_argument("-cf", "--controller-flavour", default=os.environ.get("SS_CONTROLLER_FLAVOUR"), required=not os.environ.get("SS_CONTROLLER_FLAVOUR"))
    parser.add_argument("-cn", "--controller-name", default=os.environ.get("SS_CONTROLLER_NAME"), required=not os.environ.get("SS_CONTROLLER_NAME"))

    args = parser.parse_args()  # fail parse if arg and/or env variable missing

    logger.info("================")
    logger.info("Initializing VMs")
    logger.info("================")

