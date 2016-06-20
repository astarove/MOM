import os
import sys
import subprocess
import csv
import json
from multiprocessing import Process


def collect_data():
    """Launch 'dstat' tool as stand-alone process to collect performance
    data into CSV file. Terminated outside of the process. In case of
    failure print info on the screen
    :return: None
    """
    while True:
        print(subprocess.check_output("dstat -f --output dstat.csv",
                                      stderr=subprocess.STDOUT,
                                      shell=True))


def run_scenario(uri, prj_name, script, args):
    """Launcher of user' scenario
    :param uri: URI to the GIT repo
    :param prj_name: Project folder
    :param script: Name of main script
    :param args: Arguments of the script
    :return: None
    """
    __clone_from_git(uri)
    __open_prj(prj_name)
    __launch_script(script, args)


def __clone_from_git(uri):
    """Clone repo from GIT. Removes old folder if exists
    :param uri: URI to repo in GIT
    :return: None
    """
    if os.path.isdir(uri.split('/')[-1]):
        os.system("rm -rf %s" % uri.split('/')[-1])
    os.system("git clone %s" % uri)


def __open_prj(prj_name):
    """Changes current work dir on correct
    :param prj_name: Name of project directory
    :return: None
    """
    os.chdir(prj_name)


def __launch_script(script, args):
    """Launches required script. The results of script is converts into JSON
    format 'script': 'result' and sends on the screen
    :param script: Name of script
    :param args: Additional script parameters (not required)
    :return: None
    """
    cmd = ' '.join([i for i in args])
    out = subprocess.check_output("%s %s" % (script, cmd),
                                  stderr=subprocess.STDOUT,
                                  shell=True)
    print("{\n    \"% %\": [\"%\"]".format(
          (script, cmd, '","'.join(out.strip().split('\n')))))
    print("}")


def __get_stat(data, index):
    """Collect numeric data from dictionary according required column
    :param data: Dictionary with numeric data
    :param index: Number of required column
    :return: list of required data
    """
    result = []
    for count, row in data.items():
        result.append([int(count), float(row[index])])
    return result


def __parse_csv():
    """Parses CSV file, converts data into JSON format and print it on the screen
    :return: None
    """
    # Parse source file
    with open('dstat.csv') as csvfile:
        reader = csv.reader(csvfile)

        # Skip first 5 lines which contain necessary information
        [reader.next() for _ in range(5)]
        # Read first line of headers
        group_titles = filter(lambda x: x, reader.next())

        # Read second line of headers
        column_titles = reader.next()

        stat = {}  # Store dict with unsorted numeric data
        for i, row in enumerate(reader, 0):
            stat[i] = row

    # Sort data according headers
    struct = {"complete": []}  # Store dict with structured data
    start_indx = 0  # Store start position for offset
    for group_id, group in enumerate(group_titles, 0):
        offset = 2
        # In case of several CPUs keep data for each CPU in separate dict
        if 'cpu' in group:
            offset = 6
        # Request data which correspond required column
        struct['complete'].append({'title': group,
                                   'plugin_name': 'Lines',
                                   'data':[]})
        for indx, title in enumerate(
                             column_titles[start_indx:start_indx+offset], 0):
            struct['complete'][group_id]['data'].append([title])
            struct['complete'][group_id]['data'][indx].append(__get_stat(stat, start_indx+indx))
            pass
        # Keep final position as a start point for next iterations
        start_indx += offset

    # Convert structured data into CSV and print it on standard output
    json.dump(struct, sys.stdout)
    sys.stdout.write('\n')


def __finalize(exit_code=0):
    """Tells Rally what task was finished.
    :param exit_code: O - good (default), Not 0 - not good
    :return: None
    """
    subprocess.check_output("exit %d" % exit_code, shell=True)


if __name__ == '__main__':
    """Script launches user scenario and collect performance data for analysis
    Script expects at least tree parameters:
        URI - uri to GIT repo
        PRJ - work folder
        SCR - script
    plus one not required:
        ARG - arguments of script, which can contains conveyor of commands
    """
    exit_status = 0
    if not sys.argv[1]:
        print("URI is missed")
        exit_status = 1
    elif not sys.argv[2]:
        print("Workdir is missed")
        exit_status = 1
    elif not sys.argv[3]:
        print("Name of script/command is missed")
        exit_status = 1
    else:
        # Install 'dstat' utility
        try:
            print(subprocess.check_output("sudo apt-get install dstat -y",
                                          stderr=subprocess.STDOUT,
                                          shell=True))
            pass
        except Exception:
            pass
        # Prepare user' script
        p1 = Process(target=run_scenario,
                     args=(sys.argv[1], sys.argv[2],
                           sys.argv[3], list(sys.argv[4:])))
        # Prepare collector of performance' data
        p2 = Process(target=collect_data)

        # Launch both process separately
        p1.start()
        p2.start()

        # Wait for ending af user' script and terminate performance' collector
        p1.join()
        p2.terminate()

        # Prepare collected data
        __parse_csv()
    # finalize script with correct status
    __finalize(exit_status)
