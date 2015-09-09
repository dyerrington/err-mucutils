from errbot import BotPlugin, botcmd, webhook, logging
import pandas as pd
from collections import defaultdict
from errbot.templating import tenv
import webserver, subprocess

import subprocess, re

global_store = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))  # there is a better place for this undoubtably...
trigger_store = defaultdict(dict)

class mucutils(BotPlugin):

    store_file          =   'plugins/err-mucutils/muc.cache'
    trigger_store_file  =   'plugins/err-mucutils/triggers.cache'
    channel             =   "dyerrington@chat.livecoding.tv"
    nickname            =   'WilfordII'
       
    def activate(self):

         self.restore_store()
         super(mucutils, self).activate()

         self.start_poller(60 * 30, self.say_topic)

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

        print "\n\n\n\n\n\n\nrunning restore_store()"

        try:
            store = pd.read_pickle(self.store_file)
            for key, value in store.iloc[0].to_dict().items():
                global_store[key]   =   value
                print 'setting ', key, ' to: ', value
        except:
            self.save_store()

        try:
            store = pd.read_pickle(self.trigger_store_file)
            for key, value in store.iloc[0].to_dict().items():
                trigger_store[key]   =   value
                print 'setting ', key, ' to: ', value
        except:
            self.save_store()

            # self.restore_store()
        # print "Restoring!!!!     ", global_store

    def save_store(self):
        # print 'saving', store.head()
        print "attempting to save store: ", global_store
        store = pd.DataFrame(global_store, index=global_store.keys())
        triggers = pd.DataFrame(trigger_store, index=trigger_store.keys())

        print "our store is:", store.head()
        print "our trigger store is:", triggers.head()
        store.to_pickle(self.store_file)
        triggers.to_pickle(self.trigger_store_file)


    # Topic is announced in channel every 30 minutes (configured in poller activate())
    def say_topic(self):
        self.send(
            self.channel,
            # str(msg.frm).split('/')[0], # tbd, find correct mess.ref 
            "Current Topic: %s" % global_store['topic'],
            message_type="groupchat"#msg.type
        )
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
            self.save_store()
            return "Ok, set %s to %s" % (result[1], result[2])

        return "You're not setting anything yet you smartass!"

    @botcmd()
    def action_trigger(self, msg, args):
        result = re.split("([^ ]+) (.+)", args)
        
        if len(result) == 4:

            _, key, trigger_text, _ = result

            if key in trigger_store:
                current_triggers = list(set(trigger_store[key]))
            else:
                current_triggers = []

            current_triggers.append(trigger_text)

            trigger_store[key] = current_triggers
            self.save_store()

            return "Current triggers for %s: %s" % (key, str(current_triggers))
        else:
            return "Type it right if you wan't me to do something important, sucka!"

    @botcmd()
    def get(self, msg, args):

        print "global_store:", global_store
        print "val:", global_store[args]

        if args in global_store:
            return "%s is: %s" % (args, global_store[args])

        return "Don't know anything about %s" % args

    @botcmd()
    def saymyname(self, msg, args):

        cmd = '/usr/bin/say'

        text = "Your name is, %s" % msg.nick

        subprocess.call([cmd, text])
        return "Shh I'm talking... @%s" % msg.nick

    @botcmd()
    def say(self, msg, args):

        cmd = '/usr/bin/say'

        subprocess.call([cmd, '-v', 'Karen', args])
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
        # TBD:  make a trigger for "sleep"

        # print global_store
        # print "\n\n\n\n\n\n\n\n\n\n trigger store:", trigger_store, "\n\n\n\n\n\n\n\n"

        for key, triggers in trigger_store.items():

            # print "\n\n\n\n\n\n\n\ntriggers! ", key, triggers

            # if any(sample in msg.body for sample in triggers) and msg.nick != 'WilfordII':
            if any(key in msg.body for value in trigger_store.keys()) and msg.nick != self.nickname:

                # send messsage template:
                print "trigger_store[key]: ", key, trigger_store[key], msg.nick, msg.type
                self.send(
                    str(msg.frm).split('/')[0], # tbd, find correct mess.ref 
                    global_store[key],
                    message_type=msg.type
                )

        if any(chunk in msg.body for chunk in checks):

            if msg.nick == 'Sir Wilford II': # I think if we load the config module, we can get this -- prevents looping msgs
                return

            self.send(
                str(msg.frm).split('/')[0], # tbd, find correct mess.ref 
                "Yeah sorry. There's a problem with OSX and OBS software we use to stream. Most people streaming on OSX have this issues iwth their channel.  While we wait on the next version of OBS, you will have to reload.  Sorry about that!\n\nSome users report having better results with watching from VLC using: https://github.com/chrippa/livestreamer (thanks for the link sulami)",
                message_type=msg.type
            )

    def callback_presence(self, presence):

        # self.send(
        #     "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
        #     "There was a presence change.. everyone grab your wallets %s" % presence,
        #     message_type="groupchat"
        # )

        # params = presence.split(' ')
        # parsed = {}        

        # for param in params:

        #     key, value  =   param.split(':')
        #     parsed[key] =   value




        logging.warning('presence change!!!')
        logging.warning(presence)
        print "\n\n\n\n\n\n\n\n\n\n\n PRESENCE!", presence.__dict__

        if presence.nick in ['drmjg'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "The doctor has landed!",
                message_type="groupchat"
            )
            subprocess.call(['say', '-v', '"Good News"', 'The doctor has landed!'])



        if presence.nick in ['davinci83', 'trump', 'michgeek', 'unicorn'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "The %s is in the house!" % presence.nick,
                message_type="groupchat"
            )
            subprocess.call(['say', '-v', 'Trinoids', 'The %s is in the house!' % presence.nick])


        print "\n\n\n\n\n\n\n\n\n\n\n PRESENCE!", presence

    def callback_room_joined(self, room):

        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "I have returned... Muwahahahaha!",
            message_type="groupchat"
        )

        logging.warning('OMG logged something!!!') # room == room@chat.livecoding.tv
        logging.warning(room)
