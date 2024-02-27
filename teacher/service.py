from utils.sqlalchemy import SqlAlchemySession
from Student.models  import Student, Course, Takes, Department, Instructor
from sqlalchemy import text

sql_alchemy_session = SqlAlchemySession()

from datetime import datetime, timedelta




def get_depatment_courses(department_id):
    values = {'dept_id':department_id}
    #statment = "SELECT * FROM course WHERE course.dept_id_id= :dept_id;"
    #temp = sql_alchemy_session.get_data_with_values(statment, values)
    result = {}
    query = text("SELECT * FROM course WHERE course.dept_id_id= :dept_id;")
    temp = sql_alchemy_session.get_data_with_values(query,values)
    for row in temp:
        result[row.course_id] = row.course_name
    return result

def get_teacher_courses(mail):
    values = {'mail':mail}
    #statment = "SELECT * FROM teaches WHERE teaches.mail_id= :mail;"
    #temp = sql_alchemy_session.get_data_with_values(statment, values)
    result = []
    query = text("SELECT * FROM teaches WHERE teaches.mail_id= :mail;")
    temp = sql_alchemy_session.get_data_with_values(query,values)
    for row in temp:
        result.append(row.course_id_id)
    return result

def get_department_students(dept_id):
    values = {'dept_id':dept_id}
    statment = text("SELECT student.student_id, student.std_name, student.photo FROM student WHERE student.department= :dept_id;")
    results = sql_alchemy_session.get_data_with_values(statment, values)
    student_id_name = {}

    for result in results:
        student_id_name[result.student_id] = (result.std_name, result.photo)

    return student_id_name

def get_students_per_course(course_id, dept_id):
    student_id_name = get_department_students(dept_id)
    values = {'course_id':course_id}
    statment = text("SELECT * FROM takes WHERE takes.course_id_id= :course_id;")
    results = sql_alchemy_session.get_data_with_values(statment, values)
    students = []
    #print("hERE")
    for result in results:
        students.append((student_id_name.get(result.student_id_id)[0],result.student_id_id, result.grade, result.attendace_percentage, student_id_name.get(result.student_id_id)[1]))
    #print(students)
    return students

def get_attendance_register(course_id, dept_id):
    student_id_name = get_students_per_course(course_id, dept_id)
    student_name_attendance = {}

    for data in student_id_name:
        values = {'course_id':course_id, 'student_id':data[1]}
        statment = text("SELECT * FROM dailyattendance as d WHERE d.course_id_id= :course_id and d.student_id_id= :student_id;")
        results = sql_alchemy_session.get_data_with_values(statment, values)
        #sql_alchemy_session.expire_all()
        statuses = []
        for result in results:
            if result.status == True:
                status = 'Present'
            else:
                status = 'Absent'
            date = str(result.date.day)+'-'+str(result.date.month)+'-'+str(result.date.year)
            statuses.append((date,status))

        student_name_attendance[data[0]] = statuses

    return student_name_attendance

# def get_attendance_register(course_id, dept_id):
#     student_id_name = get_students_per_course(course_id, dept_id)
#     student_name_attendance = {}
#     all_dates = get_all_dates_for_course(course_id)

#     for data in student_id_name:
#         values = {'course_id': course_id, 'student_id': data[1]}
#         query = text("SELECT * FROM dailyattendance as d WHERE d.course_id_id= :course_id and d.student_id_id= :student_id;")
#         results = sql_alchemy_session.get_data_with_values(query, values)
        
#         statuses = []
#         for result in results:
#             if result.status == True:
#                 status = 'Present'
#             else:
#                 status = 'Absent'
#             date = str(result.date.day)+'-'+str(result.date.month)+'-'+str(result.date.year)
#             statuses.append((date, status))

#         corrected_statuses = correct_attendance_list(statuses, all_dates)
#         student_name_attendance[data[0]] = corrected_statuses

#     return student_name_attendance


# def correct_attendance_list(att_list, dates):
#     dates_in_list = []

#     for v in att_list:
#         dates_in_list.append(v[0])
    
#     for i, date in enumerate(dates):
#         if date not in dates_in_list:
#             att_list.insert(i,(date, 'Absent'))

#     return att_list

# def correct_attendance_list(att_list, dates):
#     dates_in_list = [v[0] for v in att_list]
#     corrected_list = att_list.copy()
    
#     for i, date in enumerate(dates):
#         if date not in dates_in_list:
#             corrected_list.insert(i, (date, 'Absent'))

#     return corrected_list

def correct_attendance_list(att_list, dates):
    # Convert dates to a set for faster lookup
    dates_set = set(dates)
    
    # Filter the attendance list to only include records for the given dates
    corrected_list = [record for record in att_list if record[0] in dates_set]

    return corrected_list


def get_all_dates_for_course(course_id):
    # Assuming you have a table that stores these dates, modify the query accordingly
    query = text("SELECT distinct date FROM dailyattendance as d WHERE d.course_id_id= :course_id ORDER BY date;")
    results = sql_alchemy_session.get_data_with_values(query, {'course_id': course_id})

    # Format the date as 'dd-mm-yyyy'
    return [result.date.strftime('%d-%m-%Y') for result in results]

def get_week_ranges(dates):
    weeks = []
    for date in dates:
        date_obj = datetime.strptime(date, '%d-%m-%Y')
        start = date_obj - timedelta(days=date_obj.weekday())  # Monday
        end = start + timedelta(days=6)  # Sunday
        week_range = f"{start.strftime('%d-%m-%Y')} to {end.strftime('%d-%m-%Y')}"
        weeks.append(week_range)
    return weeks