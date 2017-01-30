#!/usr/bin/python
import os
import time
from daemon import runner
from slackclient import SlackClient
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser

DEPLOY_DAEMON_PID = "/tmp/ytbot.pid"
DEPLOY_DAEMON_ERROR = "/tmp/ytbot.log"

# YTBOT id
AT_BOT = "<@" + os.environ.get('YT_BOT_ID') + ">"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('YT_BOT_TOKEN'))


# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = os.environ.get('DEVELOPER_KEY')
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

class YtBot():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = DEPLOY_DAEMON_ERROR
        self.pidfile_path = DEPLOY_DAEMON_PID
        self.pidfile_timeout = 5

    def run(self):
        READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
        if slack_client.rtm_connect():
            print("YtBot connected and running!")
            while True:
                command, channel = parse_slack_output(slack_client.rtm_read())
                if command and channel:
                    handle_command(command, channel)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")

def youtube_search(term):
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

  # Call the search.list method to retrieve results matching the specified
  # query term.
  search_response = youtube.search().list(
    q=term,
    part="id,snippet",
    maxResults=1,
    safeSearch="none",
    type="video"
  ).execute()

  videos = []

  # Add each result to the appropriate list, and then display the lists of
  # matching videos, channels, and playlists.
  for search_result in search_response.get("items", []):
    videos.append("https://youtu.be/%s" % search_result["id"]["videoId"])

  return ''.join(videos)

def handle_command(command, channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    args = ' '.join(command.split(' ')[1:])
    video = youtube_search(args)
    print video
    response = video
    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel']
    return None, None

if __name__ == "__main__":
    app = YtBot()
    daemon_runner = runner.DaemonRunner(app)
    daemon_runner.do_action()

