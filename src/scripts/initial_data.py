# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import codecs
import csv
import getopt
import os
import shlex
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

___doc___ = """Script to create users. Execute without parameters for help"""

def get_column_value_list(filenames, column_name, debug=False):
    """
    Function that given a set of filenames returns the list of values
    concatenating all the columns with name "column_name"
    :param filenames:
    :param column_name:
    :return:
    """

    result = []
    for file_name in filenames:

        # Open the file for reading
        file_in = codecs.open(file_name, 'rU')
        dialect = csv.Sniffer().sniff(file_in.read(1024))
        file_in.seek(0)
        data_in = csv.reader(file_in, dialect=dialect, delimiter=str(','))

        if debug:
            print('Parsing file ' + file_name)

        line_number = 0
        header_detected = False
        col_idx = -1
        for data in data_in:
            # Count the line number to flag anomalies
            line_number += 1

            # If mark has not been detected yet
            if not header_detected:
                if column_name not in data:
                    # Line does not match, skip it
                    continue

                # At this point the column has been detected
                header_detected = True

                # Get index of the column
                col_idx = data.index(column_name)

                # Proceed with the following lines
                continue

            # Safety check. If something went wrong when the CSV file was
            # exported, it is very likely that the string #REF! is present. If
            # so, notify and stop.
            if '#REF!' in data or '#VALUE' in data:
                print('Line', line_number, 'contains incorrect data',
                      file=sys.stderr)
                sys.exit(1)

            # At this point we are processing a data line

            # If the number of fields does not match then number of columns Flag!
            if col_idx >= len(data):
                print('Mismatched line', line_number, 'skipping',
                      file=sys.stderr)
                continue

            # append the string
            result.append(data[col_idx])

    return result


def create_users(emails, password, group=None, debug=False):
    """
    Given a list of emails, create demo users with the initial password,
    make them members of the given group
    :param emails: List of emails
    :param password: Password to assign to all users
    :param group: Make users members of this group (if given)
    :param debug: Boolean controlling the printing of debug messages
    :return: Effect in the database

    """

    for email in emails:
        # Get or create the user
        user, created = get_user_model().objects.get_or_create(email=email)
        if created:
            user.name ='User Name'
            user.set_password(password)
            user.save()

        if debug and created:
            print('User ' + email + ' created.')

        if not group:
            # No need to add to group
            continue

        if group not in user.groups.all():
            if debug:
                print('Adding user ' + user.email + ' to group ' +
                      group.name)

            user.groups.add(group)
            user.save()


def run(*script_args):
    """
    Script to create superuser, group and users in the platform from a CSV file
    with a column containing email addresses. Invocation example:

    python manage.py runscript create_users \
           --script-args "-d -i -e 'emailcolumn' users.csv"

    :param script_args: Arguments given to the script.
            -d Turns on debug
            -i make users members of the instructor group (def. False)
            -e <string> email column name (def. email)
            <filename> CSV filename containing the data
    :return: Changes reflected in the dt

    The script executed three tasks:

    1) Creates the superuser from the values of the environment variables
       (if present)
       SUPERUSER_NAME
       SUPERUSER_PASSWORD

    2) Creates the group "instructor" if needed

    3) Process the CSV files (if given) by selecting the column with the given
       name (option -e) or 'email' and creating the users accordingly.
    """

    # If there is no argument given, bomb out.
    if len(script_args) == 0:
        print(run.__doc__)
        sys.exit(1)

    # Parse the arguments
    argv = shlex.split(script_args[0])

    # Default values for the arguments
    debug = False
    email_column_name = 'email'
    make_instructors = False
    password = 'changethepassword'

    # Parse options
    try:
        opts, args = getopt.getopt(argv, "de:ip:")
    except getopt.GetoptError as e:
        print(e.msg)
        print(run.__doc__)
        sys.exit(2)

    # Store option values
    for optstr, value in opts:
        if optstr == "-d":
            debug = True
        elif optstr == "-i":
            make_instructors = True
        elif optstr == "-e":
            email_column_name = value
        elif optstr == "-p":
            password = value

    filenames = args

    if debug:
        print('Options:')
        print(' Debug:' + str(debug))
        print(' Email column name:', email_column_name)
        print(' Make instructors:', str(make_instructors))
        print(' Default password: ', password)
        print(' Files: ' + ', '.join(filenames))

    if debug:
        print('Step 1: Creating the instructor group')
    group = Group.objects.filter(name='instructor').first()
    # Create the instructor group if it does not exist
    if not group:
        group = Group(name='instructor')
        group.save()
    elif debug:
        print('Group already exists. Bypassing.')
    if debug:
        print('Done')

    if debug:
        print('Step 2: Creating the superuser')
    suname = os.environ.get('SUPERUSER_NAME', None)
    if suname and not get_user_model().objects.filter(email=suname).first():
        usr = get_user_model().objects.create_superuser(
            email=suname,
            password=os.environ.get('SUPERUSER_PASSWORD', None))
        usr.groups.add(group)
        usr.save()
    elif debug:
        print('Superuser already exists. Bypassing.')
    if debug:
        print('Done')

    not_present = [x for x in filenames if not os.path.exists(x)]
    if not_present:
        print('These files were not found: ', ', '.join(not_present))
        filenames = [x for x in filenames if x not in not_present]

    if filenames == []:
        print('No files provided to create users. Terminating')
        return

    if debug:
        print('Step 3: Creating users')
    # Get the emails
    emails = get_column_value_list(filenames, email_column_name, debug)

    create_users(emails, password, group, debug)
