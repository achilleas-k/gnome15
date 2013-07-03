############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##      2013 Nuno Araujo <nuno.araujo@russo79.com>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Gnome15 - Suite of GNOME applications that work with the logitech G15
##           keyboard
##
############################################################################

'''
Gnome15 utilities to work with the system (running commands, manipulating the
filesystem, getting OS information...)
'''

from gnome15 import g15globals
import os

# Logging
import logging
logger = logging.getLogger("shell")

def run_script(script, args = None, background = True):
    """
    Runs a python script from the scripts directory.

    Keyword arguments:
    script:     the filename of the script to run
    args:       an array of arguments to pass to the script (optional, None by default)
    background: Set to run the script in the background (optional, True by default)
    """
    a = ""
    if args:
        for arg in args:
            a += "\"%s\"" % arg
    p = os.path.realpath(os.path.join(g15globals.scripts_dir,script))
    logger.info("Running '%s'" % p)
    return os.system("python \"%s\" %s %s" % ( p, a, " &" if background else "" ))

def get_command_output(cmd):
    """
    Runs a command on the shell and returns it's status code and output

    Keyword arguments:
    cmd: the command to run (either full path, or just the name if the command
         is in the %PATH)

    Returns
    A tuple with the exit code of the command and the output made on stdout by
    the command.
    Note: the last '\n' is stripped from the output.
    """
    pipe = os.popen('{ ' + cmd + '; } 2>/dev/null', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text

def mkdir_p(path):
    """
    Creates a directory and it's parents if needed unless it already exists..

    Keyword arguments:
    path: the full path to the directory to create.
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        import errno
        if exc.errno == errno.EEXIST:
            pass
        else: raise

def full_path_of_program(program_name):
    """
    Search for program_name in all the directories declared in the PATH
    environment variable

    Keyword arguments:
    program_name: the name of the program to search for

    Returns:
    Full path name of the program_name, None if program_name was not
    found in PATH.
    """
    for dir in os.environ['PATH'].split(':'):
        full_path = os.path.join(dir, program_name)
        if os.path.exists(full_path):
            return full_path
    return None

def is_program_in_path(program_name):
    """
    Checks if a program_name is available in PATH environment variable

    Keyword arguments:
    program_name: the name of the program to check

    Returns True if program_name is in PATH, else False
    """
    return full_path_of_program(program_name) != None

def get_lsb_release():
    """
    Gets the release number of the distribution

    Return:
    ret: Return code of the lsb_release command
    r:   The release number
    """
    ret, r = get_command_output('lsb_release -rs')
    return float(r) if ret == 0 else 0

def get_lsb_distributor():
    """
    Gets the Linux distribution distributor id

    Return:
    ret: Return code of the lsb_release command
    r:   The distributor id or "Unknown" if an error occurred
    """
    ret, r = get_command_output('lsb_release -is')
    return r if ret == 0 else "Unknown"

