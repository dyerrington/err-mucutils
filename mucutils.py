from errbot import BotPlugin, botcmd, webhook, logging
import pandas as pd
from collections import defaultdict
from errbot.templating import tenv
import webserver, subprocess

import subprocess, re

global_store = defaultdict()  # there is a better place for this undoubtably...

class MUCUtils(BotPlugin):

    store_file = 'plugins/err-mucutils/muc.cache'
       
    def activate(self):

         self.restore_store()
         # super(MUCUtils, self).activate()
         # self.start_poller(3, self.send_current_track)
         # self.stop_poller(self.send_current_track)

    # in progress -- thanks Allison!
    def callback_user_joined_chat(self, conn, presence):
        """
        Process a presence stanza from a chat room. In this case,
        presences from users that have just come online are
        handled by sending a welcome message that includes
        the user's nickname and role in the room.
        Arguments:
            presence -- The received presence stanza. See the
                        documentation for the Presence stanza
                        to see how else it may be used.
        """

        print "running callback_user_joined_chat()"

        if presence['muc']['nick'] != self.nick:
            self.send_message(mto=presence['from'].bare,
                              mbody="Hello, %s %s" % (presence['muc']['role'],
                                                      presence['muc']['nick']),
                              mtype='groupchat')

    def restore_store(self):
        store = pd.read_pickle(self.store_file)
        for key, value in store.iloc[0].to_dict().items():
            global_store[key]   =   value
        # print "Restoring!!!!     ", global_store

    def save_store(self):
        # print 'saving', store.head()
        print "attempting to save store: ", global_store
        store = pd.DataFrame(global_store, index=global_store.keys())
        print "our store is:", store.head()
        store.to_pickle(self.store_file)

    @botcmd
    def save(self, msg, args):
        self.save_store()
        return "Store saved!"

    @botcmd
    def restore(self, msg, args):
        self.restore_store()
        return "Store loaded!"

    @botcmd
    def hello(self, msg, args):
        return "Hello, livecoding.tv!"

    @botcmd()
    def set(self, msg, args):
        
        result = re.split("([^ ]+) (.+)", args)
        if len(result) == 4:
            global_store[result[1]] = result[2]
            return "Ok, set %s to %s" % (result[1], result[2])

        return "You're not setting anything yet you smartass!"

    @botcmd()
    def get(self, msg, args):

        print "global_store:", global_store
        print "val:", global_store[args]

        if args in global_store:
            return "%s is: %s" % (args, global_store[args])

        return "Don't know anything about %s" % args

    @botcmd()
    def say(self, msg, args):

        cmd = '/usr/bin/say'

        subprocess.call([cmd, args])
        return "Shh I'm talking... @%s" % msg.nick

    @botcmd(template="pretty")
    def pretty(self, msg, args):
    
        """Say hello to someone -- pretty styles"""
        # return tenv().get_template('pretty.html').render(name=args)
        return {'name': args}

    @botcmd()
    def track(self, msg, args):

        global_store['current_track'] = self.get_current_track()
        self.save_store()
        return "Now playing: %s" % global_store['current_track']


    """ Callback - More TBD 
  
        This callback method runs on *every* message that is received in channel or directed at the bot.

        The aim of this method will be to create a generic search / response mapper that will monitor
        a channel and look for substrings, then respond with the associated string.

        This could be useful for things like:

          - Explaining why the "the stream just died"
          - Responding to common phrases that coorespond with common threads
          - Future development

        The plan I have is to make a data driven feature that operates something like:
          >  !set <variable_name> <text/str>
          >  !set global "key(s)" <variable_name>
        
        Then, whenever someone says [key(s)], the bot responds with cooresponding <text/str> with <variable_name>

        Needs help:

          - Auth schema (boolean check from bot admin)
          - Auth flag on/off/true/false

        Proposed data schema:

        global_store = {
            'video_problem': 'bla bla bla this is why we have video problems, etc... etc...'
        }

        global_keywords = {
             'video': {
                 'keys': ['video problem', 'what happened to the video', 'should I reload'],
                 'response_key': 'video_problem'
             }
        }

    """
    def callback_message(self, msg):

        checks = ['video problem', 'stream just dropped', 'stream timed', 'stream just died', 'stream lagged', 'stream is lag', 'stream lag']

        if any(chunk in msg.body for chunk in checks):

            if msg.nick == 'Sir Wilford II': # I think if we load the config module, we can get this -- prevents looping msgs
                return

            self.send(
                str(msg.frm).split('/')[0], # tbd, find correct mess.ref 
                "Yeah sorry. There's a problem with OSX and OBS software we use to stream. Most people streaming on OSX have this issues iwth their channel.  While we wait on the next version of OBS, you will have to reload.  Sorry about that!",
                message_type=msg.type
            )
