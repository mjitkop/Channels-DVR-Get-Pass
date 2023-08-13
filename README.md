# Channels DVR Get Pass
 Retrieve a pass that triggered the recording of a program

> python cdvr_find_pass.py -h
usage: cdvr_find_pass.py [-h] -t TITLE [-e EPISODE_NUMBER] [-i IP_ADDRESS] [-p PORT_NUMBER] [-s SEASON_NUMBER] [-v]

Find which pass triggered the recording of a program.

options:
  -h, --help            show this help message and exit
  -t TITLE, --title TITLE
                        Title of the program for which you want to find the pass.
  -e EPISODE_NUMBER, --episode_number EPISODE_NUMBER
                        For a series: episode number. Not required.
  -i IP_ADDRESS, --ip_address IP_ADDRESS
                        IP address of the Channels DVR server. Not required. Default: 127.0.0.1
  -p PORT_NUMBER, --port_number PORT_NUMBER
                        Port number of the Channels DVR server. Not required. Default: 8089
  -s SEASON_NUMBER, --season_number SEASON_NUMBER
                        For a series: the season number. Not required.
  -v, --version         Print the version number and exit the program.

By default, use the URL http://127.0.0.1:8089 to query the Channels DVR server.
