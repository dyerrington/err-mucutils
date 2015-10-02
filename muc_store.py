
from sqlalchemy import Column, Integer, String, Sequence, Text, DateTime, MetaData, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# plugins/err-mucutils/mucutils.db
table = 'users'

Base = declarative_base()

class Term(Base):
    __tablename__ = 'terms'

    id          =   Column(Integer, Sequence('term_id_seq'), primary_key=True)
    term        =   Column(String(50))
    value       =   Column(Text())

    def __repr__(self):
        return "<Term(id='%d', term='%s', value='%s')> % (self.id, self.term, self.vlaue)"

class User(Base):
    
    __tablename__ = 'users'

    id          =   Column(Integer, Sequence('user_id_seq'), primary_key=True)
    nickname    =   Column(String(50))


    def __repr__(self):
        return "<User(nickname='%s'>" % (self.name)


engine  =   create_engine('sqlite:///mucutils.db', echo=True)
session =   sessionmaker()

session.configure(bind=engine)
Base.metadata.create_all(engine)

s       =  session()

ed_user =   User(nickname='ed')
term    =   Term(term='Unicorn', value='THis is a value ha awh awh awh')

s.add(ed_user)
s.add(term)

s.commit()
