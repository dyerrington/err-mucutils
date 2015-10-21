
from sqlalchemy import Column, Integer, String, Sequence, Text, DateTime, Table, create_engine, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import time

# plugins/err-mucutils/mucutils.db
Base = declarative_base()

class Term(Base):
    __tablename__ = 'terms'

    # id          =   Column(Integer, Sequence('term_id_seq'), primary_key=True)
    term        =   Column(String(50), primary_key=True)
    nickname    =   Column(String(100), nullable=False)
    value       =   Column(Text())
    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now())

    def __repr__(self):
        return "<Term(nickname='%r', term='%r', value='%r', created='%r', upated='%r')>" % (self.nickname, self.term, self.value, self.created, self.updated)

class Url(Base):

    __tablename__ = 'urls'

    url         =   Column(String(255), primary_key=True)
    nickname    =   Column(String(100), nullable=False)

    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now())

    def __repr__(self):
        return "<Giveaway(nickname='%r', url='%r', created='%r', updated='%r')>" % (self.nickname, self.url, self.created, self.updated)


class Giveaway(Base):

    __tablename__ = 'giveaway'

    nickname    =   Column(String(100), primary_key=True)
    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now())

    def __repr__(self):
        return "<Giveaway(nickname='%r', created='%r', updated='%r')>" % (self.nickname, self.created, self.updated)

class User(Base):
    
    __tablename__ = 'users'

    # id          =   Column(Integer, Sequence('user_id_seq'), )
    nickname    =   Column(String(50), nullable=False, primary_key=True)
    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now()) 

    def __repr__(self):
        return "<User(nickname='%s')>" % (self.nickname)


class Message(Base):

    __tablename__ = 'messages'

    id          =   Column(Integer(), Sequence('message_id_seq'), primary_key=True)

    nickname    =   Column(String(50), nullable=False)
    message     =   Column(Text(), nullable=False)
    message_type=   Column(String(50), nullable=False)

    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now()) 

    def __repr__(self):
        return "<Message(id=%r, nickname='%r', message='%r', message_type='%r', created='%r', updated='%r')>" % (self.id, self.nickname, self.message, self.message_type, self.created, self.updated)

class Sounds(Base):

    __tablename__ = 'sound_clips'

    id          =   Column(Integer(), Sequence('sound_id_seq'), primary_key=True)

    filename    =   Column(String(50), nullable=False)
    title       =   Column(String(50), nullable=False)
    description =   Column(Text(), nullable=False)

    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now()) 

    def __repr__(self):
        return "<Message(id=%r, filename='%r', title='%r', description='%r', created='%r', updated='%r')>" % (self.id, self.filename, self.title, self.description, self.created, self.updated)


engine  =   create_engine('sqlite:///mucutils.db', echo=True)
session =   sessionmaker()

session.configure(bind=engine)
Base.metadata.create_all(engine)

s       =  session()

# giveaway = s.merge(Giveaway(nickname="FrankButtman", updated=func.now()))
# s.commit()
# print "blalblablalbla "
# ed_user =   User(nickname='fro5t')
# term    =    s.merge(Term(term='Unicorn', value='THis is a value ha awh awh awh', nickname='ed'))
# s.add(ed_user)
# s.commit()

# time.sleep(3)

# s.query(User).filter(User.nickname == 'fro5t').update({'nickname': 'frost'})
# s.commit()

# print "result: ", s.query(Term).filter(Term.term.like("%zcsd929%")).all()
# s.commit()

# s.add(ed_user)
# try:
#     # import logging; logging.error(msg) colors text red

#     nickname = s.query(Term).filter(Term.term == 'Unicorn').one().value
#     print "\033[91m result! ", nickname
# except:
#     print "not found sucka!"

# s.commit()
