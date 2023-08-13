"""
Author: Gildas Lefur (a.k.a. "mjitkop" in the Channels DVR forums)

Description: This script takes a program title as an input and, optionally, 
             a season and an episode number if the program is a series.
             Given the provided inputs, it finds the pass that triggered 
             the recording of the program.

Disclaimer: this is an unofficial script that is NOT supported by the developers
            of Channels DVR.

Version History:
- 2023.06.24.2152: Internal use and testing.
- 2023.08.12.2305: First public release
"""

################################################################################
#                                                                              #
#                                   IMPORTS                                    #
#                                                                              #
################################################################################

import argparse, requests, sys
from datetime import datetime
from dateutil import tz

################################################################################
#                                                                              #
#                                  CONSTANTS                                   #
#                                                                              #
################################################################################

DEFAULT_PORT_NUMBER  = '8089'
LOOPBACK_ADDRESS     = '127.0.0.1'
VERSION              = '2023.08.12.2305'

################################################################################
#                                                                              #
#                               GLOBAL VARIABLES                               #
#                                                                              #
################################################################################

server_url = None

################################################################################
#                                                                              #
#                                   CLASSES                                    #
#                                                                              #
################################################################################

class Program:
    '''Attributes and methods to handle one program from the Channels DVR server.'''
    def __init__(self, program_json):
        '''Given the program in json format, extract the useful information'''
        self.program        = program_json
        self.category       = self._get_category()
        self.episode_number = self.program['Airing'].get('EpisodeNumber', None)
        self.file_name      = self._get_file_name()
        self.pass_id        = self.program.get('RuleID', None)
        self.season_number  = self.program['Airing'].get('SeasonNumber', None)
        self.title          = self.program['Airing']['Title']
        
    def _get_category(self):
        '''Extract the data in the Categories tag, if it exists.'''
        category = 'Program'
        
        categories = self.program['Airing'].get('Categories', None)
        if categories:
            category = categories[0]
            
        return category
        
    def _get_file_name(self):
        '''
        Retrieve the file name from the media info of this program.
        This only works for programs already recorded.
        '''
        file_name = None
        
        file_id = self.program.get('FileID', None)
        if not file_id:
            file_id = self.program['ID']
            
            if not '-' in file_id:
                media_info = requests.get(f'{server_url}/dvr/files/{file_id}/mediainfo.json').json()
                file_name = media_info['format']['filename']
            
        return file_name
    
    def is_imported(self):
        '''Return True or False: True if the program info contains the key "ImportPath".'''
        return "ImportPath" in self.program.keys()
        
    def is_manual_recording(self):
        '''Return True or False: True if the ID tag contains "-ch".'''
        scheduled_manually = "-ch" in self.program['ID']

        if not scheduled_manually:
            job_id = self.program.get('JobID', None)

            if job_id:
                scheduled_manually = "-ch" in job_id

        return scheduled_manually
        
################################################################################
#                                                                              #
#                                  FUNCTIONS                                   #
#                                                                              #
################################################################################

def convert_utc_time_to_local_time(utc_time):
    '''
    Takes UTC time in the format "2023-06-24T15:00Z" and convert it to the
    local time in the correct time zone.
    It will return this format: "Saturday, June 24, 2023 11:00:00 AM EDT".
    '''
    
    utc_format = "%Y-%m-%dT%H:%MZ"

    # Convert the UTC time string to a datetime object
    utc_dt = datetime.strptime(utc_time, utc_format)

    # Set the timezone for the datetime object to UTC
    utc_dt = utc_dt.replace(tzinfo=tz.tzutc())

    # Convert the UTC datetime object to the local timezone
    local_dt = utc_dt.astimezone(tz.tzlocal())

    # Format the local datetime object as a string
    local_time = local_dt.strftime('%A, %B %d, %Y %I:%M:%S %p %Z')

    return local_time

def display_server_url():
    '''Show on the screen the full URL of the Channels DVR server.'''
    print('')
    print(f'Using Channels DVR server located at: {server_url}.')
    print('')

def get_matching_programs(title, season_number, episode_number):
    '''
    Parse the list of recordings in the library and the scheduled recordings from the
    Channels DVR server, and return a list of the programs that match the given criteria.
    '''
    matching_programs = {}

    scheduled_recordings = get_scheduled_recordings()
    matching_programs = update_program_list(matching_programs, 'scheduled', \
                            scheduled_recordings, title, season_number, episode_number)

    library_programs = get_library_programs()
    matching_programs = update_program_list(matching_programs, 'library', \
                            library_programs, title, season_number, episode_number)

    return matching_programs

def get_library_programs():
    '''Retrieve all files from the Channels DVR server and return a list of Program objects.'''
    url_files = f'{server_url}/dvr/files'
    
    return [file for file in requests.get(url_files).json()]
    
def get_passes():
    '''
    Retrieve all passes from the Channels DVR server.
    Return a stripped down version of the rules in a dictionary: 
      {rule ID: pass name, ..., rule ID: pass name}
    '''
    url_rules = f'{server_url}/dvr/rules'
    
    rules = requests.get(url_rules).json()
    
    passes = {}
    for r in rules:
        passes[r['ID']] = r['Name']

    return passes
    
def get_scheduled_recordings():
    '''
    Retrieve all jobs from the Channels DVR server and return a list of Program objects.
    Only keep the ones that are not marked to be skipped.
    '''
    url_jobs  = f'{server_url}/dvr/jobs'
    
    return [recording for recording in requests.get(url_jobs).json() if not recording['Skipped']]
    
def get_server_url():
    '''Return the full URL of the Channels DVR server.'''
    return server_url
    
def update_program_list(matching_programs, key, programs, title, season_number, episode_number):
    '''
    Parse the given list of programs and save the ones that match the given criteria into the 
    matching program list. It will be formatted as a dictionary:
    {'scheduled': [program 1, ..., program N], 'library': [program 1, ..., program N]}
    
    For scheduled recordings, only keep the ones that are not marked as skipped.
    '''
    for program in programs:
        is_a_match = False
        
        if title in program['Airing']['Title']:
            is_a_match = True
            if season_number:
                is_a_match = False
                program_season_num = program['Airing'].get('SeasonNumber', None)
                if program_season_num and (season_number == program_season_num):
                    is_a_match = True
                    if episode_number:
                        is_a_match = False
                        program_episode_num = program['Airing'].get('EpisodeNumber', None)
                        if program_episode_num and (episode_number == program_episode_num):
                            is_a_match = True
            
        if is_a_match:
            current_list = matching_programs.get(key, [])
            current_list.append(Program(program))
            matching_programs[key] = current_list

    return matching_programs
    
def show_passes_for_every_program(passes, programs):
    '''Map the passes that triggered the given programs and show them on the screen.'''
    scheduled_recordings = programs.get('scheduled', None)
    library_programs     = programs.get('library', None)
    
    if scheduled_recordings:
        print('|----------------------|')
        print('| Scheduled recordings |')
        print('|----------------------|')
        print()
        display_passes(passes, scheduled_recordings)
        print()
    
    if library_programs:
        print('|-------------------|')
        print('| Library programs  |')
        print('|-------------------|')
        print()
        display_passes(passes, library_programs)
        print()

def display_passes(passes, programs):
    '''
    Parse the given programs (either scheduled recordings or library programs) and
    print the matching passes for each program.
    '''
    for program in programs:
        file_name = program.file_name
        string_to_print = f' - {program.category} "{program.title}" '

        if program.category in ["Episode", "Show", "Series"]:
            if program.season_number:
                string_to_print += f'S{program.season_number}'
            if program.episode_number:
                string_to_print += f'E{program.episode_number}'
                string_to_print += ' '
        
        raw  = get_raw_data(program)
        
        if program.is_imported():
            string_to_print += f'is an import:\n'
            string_to_print += f'    "{file_name}"\n'
        elif program.is_manual_recording():
            string_to_print += 'is a manual recording.\n'
            # Show the file name for programs already recorded
            if file_name:
                string_to_print += f'    "{file_name}"\n'
            else:
                if raw:
                    start_time = convert_utc_time_to_local_time(raw['startTime'])
                    string_to_print += f'   will be recorded on {start_time}\n'
        else:
            pass_name = passes.get(program.pass_id, None)

            if not pass_name:
                pass_name = 'nothing found!'
    
            string_to_print += f'triggered by pass: "{pass_name}"\n'
            
            if file_name:
                # Programs already recorded (in the library) have a file name
                string_to_print += f'    "{file_name}"\n'
            else:
                # Program in the schedule
                if raw:
                    # The raw data is not always provided, it depends on the source
                    start_time = raw.get('startTime', None)
                    if start_time:
                        start_time = convert_utc_time_to_local_time(start_time)
                        string_to_print += f'   will be recorded on {start_time}\n'
        
        print(string_to_print)
        
def get_raw_data(program):
    '''Return the data in Airing/Raw, if available.'''
    raw_data = None
    
    airing = program.program.get('Airing', None)
    if airing:
        raw_data = airing.get('Raw', None)
        
    return raw_data


################################################################################
#                                                                              #
#                                 MAIN PROGRAM                                 #
#                                                                              #
################################################################################

if __name__ == "__main__":
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(
                description = "Find which pass triggered the recording of a program.",
                epilog = "By default, use the URL http://127.0.0.1:8089 to query the Channels DVR server.")

    # Add the input arguments
    parser.add_argument('-t', '--title', type=str, required=True, \
                        help='Title of the program for which you want to find the pass.')
    parser.add_argument('-e', '--episode_number', type=int, default=None, \
                        help='For a series: episode number. Not required.')
    parser.add_argument('-i', '--ip_address', type=str, default=LOOPBACK_ADDRESS, \
                        help=f'IP address of the Channels DVR server. Not required. Default: {LOOPBACK_ADDRESS}')
    parser.add_argument('-p', '--port_number', type=str, default=DEFAULT_PORT_NUMBER, \
                        help=f'Port number of the Channels DVR server. Not required. Default: {DEFAULT_PORT_NUMBER}')
    parser.add_argument('-s', '--season_number', type=int, default=None, \
                        help='For a series: the season number. Not required. ')
    parser.add_argument('-v', '--version', action='store_true', help='Print the version number and exit the program.')

    # Parse the arguments
    args = parser.parse_args()

    # Access the values of the arguments
    episode_number = args.episode_number
    season_number  = args.season_number
    server_url     = f'http://{args.ip_address}:{args.port_number}'
    title          = args.title
    version        = args.version

    # If the version flag is set, print the version number and exit
    if version:
        print(VERSION)
        sys.exit()

    # All good. Let's go!
    
    display_server_url()
    
    print('Looking for matches...\n')
    
    passes   = get_passes()
    programs = get_matching_programs(title, season_number, episode_number)
    
    if not programs:
        print('no matches found.')
        print('')
    
    show_passes_for_every_program(passes, programs)
