
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

class User(Base):
    
    __tablename__ = 'users'

    # id          =   Column(Integer, Sequence('user_id_seq'), )
    nickname    =   Column(String(50), nullable=False, primary_key=True)
    created     =   Column(DateTime(), default=func.now())
    updated     =   Column(DateTime(), onupdate=func.now())

    def __repr__(self):
        return "<User(nickname='%s')>" % (self.nickname)


engine  =   create_engine('sqlite:///mucutils.db', echo=False)
session =   sessionmaker()

session.configure(bind=engine)
Base.metadata.create_all(engine)

s       =  session()

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
