# Web-Response-Analyzer
This Python script is designed to analyze the responses from multiple GET requests to a specific URL. It’s particularly useful for identifying dynamic parameters and observing changes in responses.

Features
Make Multiple GET Requests: The script can make multiple GET requests to a given URL using curl and return the responses.
Identify Dynamic Parameters: It can identify potential dynamic parameters by analyzing multiple responses.
Find Unique Identifiers: The script can find a unique identifier in the original response that is not present in the example.com response.
Check Response Change: It checks for changes in response and returns observed differences.
Save Flagged URLs: The script can save flagged URLs to a text file.
Run Recollapse Tool: It can run the recollapse tool and save results to a text file.
Usage
This script is intended to be run from the command line. It requires Python 3.x and the following Python libraries: os, subprocess, re, hashlib, and logging.
