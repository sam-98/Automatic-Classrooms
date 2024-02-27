from utils.sqlalchemy import SqlAlchemySession
from Student.models  import Student, Course, Takes, Department

sql_alchemy_session = SqlAlchemySession()

statment = "SELECT * FROM course;"
temp = sql_alchemy_session.get_data(statment)
for t in temp:
    print(t)