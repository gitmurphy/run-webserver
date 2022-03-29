#!/usr/bin/python3

"""A tiny Python program to check that nginx is running.
Try running this program from the command line like this:
  python3 check_webserver.py
"""

import subprocess

# ps - A : report a snapshot of current processes - select all processes
# grep nginx :

def checknginx():
  try:
    cmd = 'ps -A | grep nginx'

    subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Nginx Server IS running")

  except subprocess.CalledProcessError:
    print("Nginx Server IS NOT running")

# Define a main() function.
def main():
    checknginx()

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
  main()
