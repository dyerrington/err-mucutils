from errbot import BotPlugin, botcmd, webhook, logging
from errbot.backends.base import Message, MUCRoom, Presence, RoomNotJoinedError

import pandas as pd, arrow, sqlite3 as db
from collections import defaultdict
from errbot.templating import tenv
import webserver, subprocess
import random, gntp.notifier


import subprocess, re


# simple ORM via sqlalchemy
# from sqlalchemy import Column, Integer, String, Sequence, Text, DateTime, MetaData, Table, create_engine
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import muc_orm as orm



global_store = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))  # there is a better place for this undoubtably...
trigger_store = defaultdict(dict)
stats_store = defaultdict(list)
karma_store = defaultdict(list)

""" 
    Note to self - TBD:

    - Vote / kick
    - !say thresh
    - !say off / on vote
    - join / leave stats
    - time based gammafication
    - spotify: vote skip track
    - music links: youtube
    - !lastseen [username]

"""

class mucutils(BotPlugin):

    store_file          =   'plugins/err-mucutils/muc.cache'
    trigger_store_file  =   'plugins/err-mucutils/triggers.cache'
    stats_store_file    =   'plugins/err-mucutils/stats.cache'
    karma_store_file    =   'plugins/err-mucutils/karma.cache'
    """ starting to move code over to SQLite3 """
    dsn = {
        'db_file': 'plugins/err-mucutils/mucutils.db',
    }

    channel             =   "dyerrington@chat.livecoding.tv"
    nickname            =   'WilfordII'
    say_flag            =   "On"
    say_vote_on         =   set()
    say_vote_off        =   set()
    say_vote_threashold =   3

    graylist            =   ['fro5t2']

    """ ORM config """
    # Base                =   declarative_base()

    def activate(self):

        self.set_orm()

        self.restore_store()
        super(mucutils, self).activate()

        self.start_poller(60 * 30, self.say_topic)

        # super(MUCUtils, self).activate()
        # self.start_poller(3, self.send_current_track)
        # self.stop_poller(self.send_current_track)

    def set_orm(self):
        
        self.engine     =   create_engine('sqlite:///plugins/err-mucutils/mucutils.db', echo=True)
        self.session    =   sessionmaker()
        self.session.configure(bind=self.engine)
        orm.Base.metadata.create_all(self.engine)

        self.dbh        =   self.session()


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

    def restore_store_tbd(self, store_object=False, store_file=False):

        print "\n\n\n\n\n\n\nrunning restore_store()"

        try:
            store = pd.read_pickle(store_file)
            for key, value in store.iloc[0].to_dict().items():
                store_object[key]   =   value
                print 'setting ', key, ' to: ', value
        except:
            self.save_store()

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

        try:
            store = pd.read_pickle(self.stats_store_file)
            for key, value in store.iloc[0].to_dict().items():
                stats_store[key]   =   value
                print 'setting ', key, ' to: ', value
        except:
            self.save_store()


        try:
            store = pd.read_pickle(self.karma_store_file)
            for key, value in store.iloc[0].to_dict().items():
                karma_store[key]   =   value
                print 'setting ', key, ' to: ', value
        except:
            self.save_store()

            # self.restore_store()
        # print "Restoring!!!!     ", global_store

    def save_store(self):
        # print 'saving', store.head()
        print "attempting to save store: ", global_store
        store       =   pd.DataFrame(global_store, index=global_store.keys())
        triggers    =   pd.DataFrame(trigger_store, index=trigger_store.keys())
        stats       =   pd.DataFrame(stats_store, index=stats_store.keys())
        karma       =   pd.DataFrame(karma_store, index=karma_store.keys())

        print "our store is:", store.head()
        print "our trigger store is:", triggers.head()
        store.to_pickle(self.store_file)
        triggers.to_pickle(self.trigger_store_file)
        stats.to_pickle(self.stats_store_file)
        karma.to_pickle(self.karma_store_file)

    @botcmd()
    def crash(self, msg, args):
        import pdb

        for item in self.query_room(self.channel).occupants:
            print item
        # print room.occupants()


        # print backends.base.MUCRoom.occupants
        # pdb.set_trace()
        return [user.split('/')[1] for user in self.query_room(self.channel).occupants]
    
    @botcmd()
    def say_on(self, msg, args):
        # say_vote_threashold
        self.say_vote_on.add(msg.nick)
        if len(self.say_vote_on) >= 3:
            self.say_flag = "On"
            self.say_vote_on, self.say_vote_off = set(), set()
  
            return "Vote passed.  Say turned on." 
        return "Current vote to turn say on: %d" % len(self.say_vote_on)

    @botcmd()
    def say_off(self, msg, args):
        self.say_vote_off.add(msg.nick)

        if len(self.say_vote_off) >= 3:
            self.say_flag = "Off"
            self.say_vote_on, self.say_vote_off = set(), set()
            return "Vote passed.  Say turned off." 
        return "Current vote to turn say off: %d" % len(self.say_vote_off)

    @botcmd
    def orm(self, msg, args):
        # term = orm.Term(term='goodread', value='very high value', nickname='dyerrington')
        logging.warning('orm.Base:')
        logging.warning(orm.Base)
        return "orm loaded hopefully.."

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

        # self.restore_store(store_object=global_store, store_file=self.store_file)
        # self.restore_store(store_object=trigger_store, store_file=self.trigger_store_file)
        # self.restore_store(store_object=karma_store, store_file=self.karma_store_file)
        # self.restore_store(store_object=stats_store, store_file=self.stats_store_file)

        return "Store loaded!"

    @botcmd()
    def hello(self, msg, args):
        return "Hello, livecoding.tv!"

    @botcmd()
    def update_users(self, msg, args):
        self.set_orm()
        self.dbh.merge(orm.User(nickname=msg.nick, updated=func.now()))
        self.dbh.commit()
        return "Ok updated the users table" 

    @botcmd()
    def giveaway(self, msg, args):

        return "Sorry our giveaway is closed until next time!"

        self.set_orm()
        self.dbh.merge(orm.Giveaway(nickname=msg.nick, updated=func.now()))
        self.dbh.commit()
        return "Ok you are entered to win %s!" % msg.nick

    @botcmd()
    def giveaway_winner(self, msg, args):

        if msg.nick != 'dyerrington':
            return "What do you think this is?  You can't pick a winner!"

        # random.choice(#)
        
        users = [] 

        for user in self.dbh.query(orm.Giveaway).all():
            users.append(user.nickname) 
        
        cmd         =   "/usr/bin/afplay"
        sound_file  =   "/Users/davidyerrington/soundclips/magnificent.wav"

        winner      =   random.choice(users)

        growl = gntp.notifier.GrowlNotifier(
                applicationName = "livecoding.tv Awesome Notification Business HD",
                notifications = ["New Updates","New Messages"],
                defaultNotifications = ["New Messages"]
                # hostname = "computer.example.com", # Defaults to localhost
                # password = "abc123" # Defaults to a blank password
        )

        growl.register()
        growl.notify(
            noteType = "New Messages",
            title = "%s" % winner,
            description = "You're our giveaway winner! Congrats!",
            icon = "http://vignette1.wikia.nocookie.net/goldencartoons/images/6/61/Fluttershy-my-little-pony-friendship-is-magic.png",
            sticky = True,
            priority = 1
        )

        subprocess.call([cmd, sound_file])

        return "And the winner is %s" % winner


    @botcmd()
    def set(self, msg, args):
        
        result = re.split("([^ ]+) (.+)", args)
        if len(result) == 4:

            self.set_orm()

            term    =   orm.Term(term=result[1], value=result[2], nickname=msg.nick)
            self.dbh.merge(term)
            self.dbh.commit()

            # global_store[result[1]] = result[2]
            # self.save_store()
            
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

        try:
            self.set_orm()

            result  =   self.dbh.query(orm.Term).filter(orm.Term.term == args.strip())
            value   =   result.one().value
            return "%s is: %s" % (args, value)
        except:
            return "Don't know anything about %s" % args
        

    @botcmd()
    def karma(self, msg, args):
        karma_store[args].append({msg.nick: arrow.utcnow()})
        return "Ok added karma to %s args" % args

    @botcmd()
    def saymyname(self, msg, args):

        if self.say_flag == 'Off':
            return 'Sorry, the channel voted the say command off.'

        cmd = '/usr/bin/say'
        text = "Your name is, %s" % msg.nick

        subprocess.call([cmd, text])
        return "Shh I'm talking... @%s" % msg.nick

    @botcmd()
    def dolan(self, msg, args):

        if self.say_flag == 'Off':
            return 'Sorry, the channel voted the say command off.'

        if msg.nick in self.graylist:
            return "Sorry %s, you turned off your say :(" % msg.nick

        cmd = '/usr/bin/say'

        subprocess.call([cmd, '-v', 'Markus', args])
        return "Eile mit Weile..Ich bin ein berliner, mein schatz... @%s" % msg.nick

    @botcmd()
    def daniel(self, msg, args):

        if self.say_flag == 'Off':
            return 'Sorry, the channel voted the say command off.'

        if msg.nick in self.graylist:
            return "Sorry %s, you turned off your say :(" % msg.nick
        
        cmd = '/usr/bin/say'

        subprocess.call([cmd, '-v', 'Daniel', args])
        return "Shh I'm talking lad... @%s" % msg.nick

    @botcmd()
    def say(self, msg, args):

        if self.say_flag == 'Off':
            return 'Sorry, the channel voted the say command off.'

        if msg.nick in self.graylist:
            return "Sorry %s, you turned off your say :(" % msg.nick

        cmd = '/usr/bin/say'

        subprocess.call([cmd, '-v', 'Karen', args])
        return "Shh I'm talking... @%s" % msg.nick

    @botcmd()
    def search(self, msg, args):

        matches = []

        results = self.dbh.query(orm.Term).filter(orm.Term.term.like("%" + args + "%")).all()

        for row in results:
            matches.append(row.term)

        if len(matches) == 1:
            return "I found one: %s" % " ".join(matches)
        elif len(matches) > 1:
            return "I found a few: %s" % ", ".join(matches)
        else:
            return "Nothing found matching %s" % args

        logging.warning("\n\n\n\n\n\n\n\n\n\n\n\n HEEEEEEEEY")
        logging.warning(args)
        return "I'm searching ok!!!!"

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

        # another test:  Is this nudejs?

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
                "Yeah sorry. There's a problem with OSX and OBS software we use to stream. Most people streaming on OSX have this issues iwth their channel.  While we wait on the next version of OBS, you will have to reload.  Sorry about that!\n\nSome users report having better results with watching from VLC using: https://github.com/chrippa/livestreamer (pip install livestreamer)\n\nTo connect via livestreamer, look for the 'rtmp' link (looks like this: http://snag.gy/3o2rA.jpg), and run livestreamer from the terminal.",
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
        #     
        
        logging.warning('presence change!!!') 
        logging.warning(presence) 

        # print "\n\n\n\n\n\n\n\n\n\n\n PRESENCE!", presence.__dict__

        if presence.nick in ['xmetrix'] and presence.status == 'online':
           
            message     =   'xmetrix: kept looking for the chapter "Lisps"'
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                message,
                message_type="groupchat"
            )
            subprocess.call(['say', '-v', 'Thomas', message])

        if presence.nick in ['drmjg'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "The doctor has landed!",
                message_type="groupchat"
            )
            subprocess.call(['say', 'The doctor has landed!'])


        if presence.nick in ['tbh'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "%s, part machine, part legend." % presence.nick,
                message_type="groupchat"
            )
            subprocess.call(['say', '-v', 'Karen', '%s, part machine, part legend.' % presence.nick])


        if presence.nick in ['davinci83', 'trump', 'michgeek', 'unicorn', 'fro5t', 'devnubby', 'dardoneli', 'the1owl', 'allisonanalytics', 'hugo_r', 'sqeezy80', 'hakim', 'rondorules', 'goodread', 'castillonis', 'zuma89'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "The %s is in the house!" % presence.nick,
                message_type="groupchat"
            )
            subprocess.call(['say', '-v', 'Trinoids', 'The %s is in the house!' % presence.nick])

 
        stats_store[presence.nick].append({str(arrow.utcnow()): str(presence.status)})

        logging.warning('stats_store is: ', stats_store)
        print stats_store



        print "\n\n\n\n\n\n\n\n\n\n\n PRESENCE!", presence

    def callback_room_joined(self, room):

        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "I have returned... Muwahahahaha!",
            message_type="groupchat"
        )

        logging.warning('OMG logged something!!!') # room == room@chat.livecoding.tv
        logging.warning(room)
