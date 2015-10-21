from errbot import BotPlugin, botcmd, webhook, logging
from errbot.backends.base import Message, MUCRoom, Presence, RoomNotJoinedError

from datetime import *; from dateutil.relativedelta import *
import humanize, Levenshtein

import pandas as pd, arrow, sqlite3 as db
from collections import defaultdict
from errbot.templating import tenv
import webserver, subprocess
import random, gntp.notifier
import time, operator


import subprocess, re


# simple ORM via sqlalchemy
# from sqlalchemy import Column, Integer, String, Sequence, Text, DateTime, MetaData, Table, create_engine
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import muc_orm as orm

# super cool human times!
attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
human_readable = lambda delta: ['%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1]) for attr in attrs if getattr(delta, attr)]

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

    sound_quiz_store    =   { 
        'state': 0,     # 0 = off, 1 = init, 2 = question, 3 = answer
        'sound_file': False,
        'answer_ordinal': 0,
        'current_answers': {}
    }

    sound_quiz_flag     =   "Off"
    sound_quiz_vote_on  =   set()


    graylist            =   ['fro5t2']

    """ ORM config """
    # Base                =   declarative_base()

    def activate(self):

        self.set_orm()

        self.restore_store()
        super(mucutils, self).activate()

        self.start_poller(60 * 30, self.say_topic)
        self.start_poller(60 * 5, self.update_user_presence)

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

    def update_user_presence(self):

        users = []

        for item in self.query_room(self.channel).occupants:

            self.set_orm()
            self.dbh.merge(orm.User(nickname=item.resource, updated=func.now()))
            self.dbh.commit()
            # update(users).where(users.c.id==5).\
            # values(name='user #5')

            users.append(item.resource)

    @botcmd()
    def seen(self, msg, args):
        """
        Find out if we've seen someone on the channel.  See also: !firstseen
        """
        try:

            NOW = datetime.now()

            result  =   self.dbh.query(orm.User).filter(orm.User.nickname == args.strip())
            user    =   result.one()
            time_units  =   human_readable(relativedelta(NOW, user.updated))
            time_str    =   " ".join(time_units)
            
            return "%s was last seen %s ago." % (args.strip(), time_str)

            # for user in users:
            #     time_units  =   human_readable(relativedelta(user.updated, user.created))
            #     time_str    =   " ".join(time_units)
            #     stats.append("%s %s" % (user.nickname, time_str))

            # return "Ok the stats: %s" % ", ".join(stats)

        except:
            return "Sorry, %s was not found." % args


    @botcmd()
    def firstseen(self, msg, args):
        """
        Find out when we first saw someone on the channel.
        """
        self.set_orm()
        # users = self.dbh.query(orm.User(nickname=args)).order_by(desc(orm.User.created)).all()



        try:
            result  =   self.dbh.query(orm.User).filter(orm.User.nickname == args.strip())
            user    =   result.one()
            time_units  =   human_readable(relativedelta(user.updated, user.created))
            time_str    =   " ".join(time_units)
            
            return "%s was first seen %s ago." % (args.strip(), time_str)

            # for user in users:
            #     time_units  =   human_readable(relativedelta(user.updated, user.created))
            #     time_str    =   " ".join(time_units)
            #     stats.append("%s %s" % (user.nickname, time_str))

            # return "Ok the stats: %s" % ", ".join(stats)

        except:
            return "Sorry, %s was not found." % args


    @botcmd()
    def crash(self, msg, args):

        print self.sound_quiz_store

        # import pdb

        # users = []

        # for item in self.query_room(self.channel).occupants:

        #     self.set_orm()
        #     self.dbh.merge(orm.User(nickname=item.resource, updated=func.now()))
        #     self.dbh.commit()
        #     # update(users).where(users.c.id==5).\
        #     # values(name='user #5')

        #     users.append(item.resource)
        #     print item._resource
        # # print room.occupants()
        # print users

        # # print backends.base.MUCRoom.occupants
        # # pdb.set_trace()
        # # [user.split('/')[1] for user in self.query_room(self.channel).occupants]
        # return ", ".join(users) 
    
    @botcmd()
    def last_links(self, msg, arg):
        
        urls = self.dbh.query(orm.Url).order_by(desc(orm.Url.updated)).limit(10).all()
        links = []

        for url in urls:
            links.append(url.url + ', ' + url.nickname)

        return "Last 10 URLs:\n%s" % "\n".join(links) 



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

    def init_soundquiz(self):

        self.sound_quiz_store['state'] = 1

        self.set_orm()
        soundclip = self.dbh.query(orm.Sounds).filter(orm.Sounds.title != None).order_by(func.random()).first()
        
        self.sound_quiz_store['sound_file'] =   soundclip
        

        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "Are you ready for the sound challege boys and girls!?",
            message_type="groupchat"
        )

        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "The challenege will start in 20 seconds.. buckle your safety belts.",
            message_type="groupchat"
        )

        subprocess.call(['/usr/bin/afplay', "/Users/davidyerrington/soundbites/wheel_theme.wav"])

        cmd = '/usr/bin/say'
        subprocess.call([cmd, '-v', 'Markus', 'Get ready.'])
        self.sound_quiz_store['state']      =   2

        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "Ok listen, then use !sound [your answer here].  Closest answer will win!",
            message_type="groupchat"
        )

        self.sound_quiz_flag            =   'On'
        self.sound_quiz_store['state']  =   2

        random_file     =   soundclip.filename
        subprocess.call(['/usr/bin/afplay', "/Users/davidyerrington/soundclips/%s" % random_file])

        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "Playback complete. 10 seconds remaining...",
            message_type="groupchat"
        )

        time.sleep(10)

        answers = []

        for user, data in self.sound_quiz_store['current_answers'].items():

            print data

            distance = Levenshtein.ratio(soundclip.title.lower(), data['answer'].lower())
            distance *= 100
            answers.append((data['ordinal'], distance, data['answer'], user))

        best_score = sorted(answers, key=lambda row: (row[1], -row[0]), reverse=True)
        best_score = best_score[0]

        if best_score[1] < 80:
            subprocess.call(['/usr/bin/afplay', "/Users/davidyerrington/soundbites/fail.mp3"])

            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "The best answer is from: %s, only %f accuracy, with %s" % (best_score[3], best_score[1], best_score[2]),
                message_type="groupchat"
            )

        elif best_score[1] >= 90:

            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "THE WINNER IS: %s with accuracy: %d" % (best_score[3], best_score[1]),
                message_type="groupchat"
            )
            
            subprocess.call(['/usr/bin/afplay', "/Users/davidyerrington/soundbites/yeah.mp3"])


        self.send(
            "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
            "The sound bite was: %s\n\n%s" % (soundclip.title, soundclip.description),
            message_type="groupchat"
        )


        # self.send(
        #     "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
        #     "debug best_score: %s" % best_score,
        #     message_type="groupchat"
        # )

        # reset states for quiz
        self.sound_quiz_flag            =   'Off'
        self.sound_quiz_store['state']  =   0
        self.sound_quiz_store['current_answers'] = {}
        self.sound_quiz_vote_on     =   set()

        
    @botcmd()
    def sound(self, msg, args):

        # 0 = off, 1 = init, 2 = question, 3 = answer
        if self.sound_quiz_flag == 'Off' and self.sound_quiz_store['state'] == 0:
            return "We're not playing soundquiz right now.  Vote to turn it on: !soundquiz"

        if self.sound_quiz_store['state'] == 1:
            return "%s wait for the sound to play.." % msg.nick

        self.sound_quiz_store['current_answers'].update({msg.nick: { 'answer': args, 'ordinal': self.sound_quiz_store['answer_ordinal']}})
        self.sound_quiz_store['answer_ordinal'] += 1

        print self.sound_quiz_store
        return "%s thinks it's %s" % (msg.nick, args)

    @botcmd()
    def soundquiz(self, msg, args):

        if self.sound_quiz_flag == 'Off':
            self.sound_quiz_vote_on.add(msg.nick)

            if len(self.sound_quiz_vote_on) == 2:
                self.sound_quiz_flag        =   'On'
                self.sound_quiz_vote_on     =   set()
                self.init_soundquiz()

            return "%d more votes needed to play sound quiz!  Current vote set:  %s" % (2 - (len(self.sound_quiz_vote_on)), self.sound_quiz_vote_on)


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
        self.set_orm()

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


    def save_url(self, matches, nickname):

        for match in matches:
            self.set_orm()
            self.dbh.merge(orm.Url(url="%s://%s%s" % match, nickname=nickname, updated=func.now()))
            self.dbh.commit()

    def insert_message(self, nickname, message, message_type):
        self.set_orm()
        self.dbh.merge(orm.Message(nickname=nickname, message=message, message_type=message_type, updated=func.now()))
        self.dbh.commit()

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

        # log every message, for posterity 
        
        if msg.nick != self.nickname:
            self.insert_message(msg.nick, msg.body, msg.type)

        checks = ['video problem', 'stream just dropped', 'stream timed', 'stream just died', 'stream lagged', 'stream is lag', 'stream lag']
        # TBD:  make a trigger for "sleep"

        # another test:  Is this nudejs?

        # print global_store
        # print "\n\n\n\n\n\n\n\n\n\n trigger store:", trigger_store, "\n\n\n\n\n\n\n\n"

        p = re.compile("/((?:(http|https|Http|Https|rtsp|Rtsp):\/\/(?:(?:[a-zA-Z0-9\$\-\_\.\+\!\*\'\(\)\,\;\?\&\=]|(?:\%[a-fA-F0-9]{2})){1,64}(?:\:(?:[a-zA-Z0-9\$\-\_\.\+\!\*\'\(\)\,\;\?\&\=]|(?:\%[a-fA-F0-9]{2})){1,25})?\@)?)?((?:(?:[a-zA-Z0-9][a-zA-Z0-9\-]{0,64}\.)+(?:(?:aero|arpa|asia|a[cdefgilmnoqrstuwxz])|(?:biz|b[abdefghijmnorstvwyz])|(?:cat|com|coop|c[acdfghiklmnoruvxyz])|d[ejkmoz]|(?:edu|e[cegrstu])|f[ijkmor]|(?:gov|g[abdefghilmnpqrstuwy])|h[kmnrtu]|(?:info|int|i[delmnoqrst])|(?:jobs|j[emop])|k[eghimnrwyz]|(?:lyip|l[abcikorstuvy])|(?:mil|mobi|museum|m[acdeghklmnopqrstuvwxyz])|(?:name|net|n[acefgilopruz])|(?:org|om)|(?:pro|p[aefghklmnrstwy])|qa|r[eouw]|s[abcdeghijklmnortuvyz]|(?:tel|travel|trade|t[cdfghjklmnoprtvwz])|u[agkmsyz]|v[aceginu]|w[fs]|(?:yoky|y[etu])|z[amw]))|(?:(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9])\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9]|0)\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9]|0)\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])))(?:\:\d{1,5})?)(\/(?:(?:[a-zA-Z0-9\;\/\?\:\@\&\=\#\~\-\.\+\!\*\'\(\)\,\_])|(?:\%[a-fA-F0-9]{2}))*)?(?:\b|$)/gi")
        matches = p.findall(msg.body)

        if matches and msg.nick != 'WilfordII':
            print "Saving URL from %s" % msg.nick
            self.save_url(matches, msg.nick)

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

        if presence.nick in ['hugo_r'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "Hugo Always Win!",
                message_type="groupchat"
            )
            subprocess.call(['say', 'Hugo Always Win!'])



        if presence.nick in ['tbh'] and presence.status == 'online':
            self.send(
                "dyerrington@chat.livecoding.tv", # tbd, find correct mess.ref 
                "%s, part machine, part legend." % presence.nick,
                message_type="groupchat"
            )
            subprocess.call(['say', '-v', 'Karen', '%s, part machine, part legend.' % presence.nick])


        if presence.nick in ['davinci83', 'trump', 'michgeek', 'unicorn', 'fro5t', 'devnubby', 'dardoneli', 'the1owl', 'allisonanalytics', 'sqeezy80', 'hakim', 'rondorules', 'goodread', 'castillonis', 'zuma89', 'modzer0', 'pos', 'brandonbahret'] and presence.status == 'online':
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
