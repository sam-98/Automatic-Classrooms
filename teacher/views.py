from django.shortcuts import render, redirect
from django.http import HttpResponse
from Student.models import Instructor, Department, Course, Takes, Teaches, Student, DailyAttendance
from .service import get_week_ranges,get_depatment_courses, get_teacher_courses, get_department_students, get_students_per_course, get_attendance_register, correct_attendance_list
from django.core.files.storage import default_storage, FileSystemStorage
# from utils.facedetection import get_face_encodings, get_minimum_similiarity
from utils.detectionotm import get_face_encodings, get_minimum_similiarity
from attendancesystems.settings import BASE_DIR, MEDIA_ROOT
import os, cv2
from datetime import datetime
import pickle as pkl
import numpy as np
from utils.assignments import hungarian_algorithm, ans_calculation
import time
from django.shortcuts import redirect
from django.db.models import Count, Q


from django.core.mail import send_mail
# Create your views here.
sim_threshold = 0.3

def login_page(request):
    if 'usernameT' in request.session:
        return redirect(login_to_home)
    else:
        return render(request, 'loginpage.html', {'role':'teacher'})

def registration_page(request):
    return render(request, 'registrationpage.html', {'role':'teacher'})


def registration(request):
    try:
        if request.method == 'POST':
            name = request.POST['name']
            department = request.POST['department']
            password = request.POST['password']
            repassword = request.POST['repassword']
            mail = request.POST['mail']
            mobile = request.POST['mobile']
            if password == repassword and name != "" and password != "":
                ins =  Instructor(mail=mail, instructor_name=name,department=department, password=password, mobile=mobile)
                ins.save()
                print("Data has been writteen to the db")
                return render(request, 'registrationmessage.html')
            else:
                print("Please check details entered")
                return redirect(registration_page)
    except Exception:
        print(Exception)
        return render(request, 'error.html')


def login_to_home(request):

    try:
        if request.method == 'POST':
            mail = request.POST['username']
            password = request.POST['password']

            user_data = Instructor.objects.get(mail=mail)
            deptname = Department.objects.get(dept_id=user_data.department)
            user = {'user':user_data, 'deptname':deptname, 'role':'teacher'}
            if user_data.password == password:
                request.session['usernameT'] = mail
                request.session['deptidT'] = user_data.department
                return render(request, 'home1.html', user)
            else:
                return render(request, 'loginpage.html')

        if request.method == 'GET':
            if 'usernameT' in request.session:
                mail = request.session['usernameT']
                user_data = Instructor.objects.get(mail=mail)
                deptname = Department.objects.get(dept_id=user_data.department)
                user = {'user':user_data, 'deptname':deptname, 'role':'teacher'}
                return render(request, 'home1.html', user)
            else:
                return render(request, 'loginpage.html')
    except Exception:
        print(Exception)
        return render(request, 'error.html')
        

def logout(request):
    if 'usernameT' in request.session:
        request.session.flush()
    return render(request, 'loginpage.html')


def courses(request):
    if 'usernameT' not in request.session:
        return redirect(login_page)
        
    mail = request.session['usernameT']
    dept_id = request.session['deptidT']
    #std_courses = Takes.objects.filter(student_id=student_id)
    #context = {'courses':std_courses}

    dept_courses = get_depatment_courses(dept_id)
    teacher_courses = get_teacher_courses(mail)
    data = []

    for course in teacher_courses:
        data.append((dept_courses.get(course), "courses/"+course))
    return render(request, 'courses.html', {'data':data})


def addcourse(request):
    
    try:
        if request.method == 'GET':
            deptid = request.session['deptidT']
            dept_courses = Course.objects.filter(dept_id = deptid)
            return render(request, 'teacher_addcourses.html', {'courses':dept_courses})

        if request.method == 'POST':
            course_name = request.POST['coursename']
            mail = request.session['usernameT']
            deptid = request.session['deptidT']
            dept_courses = get_depatment_courses(deptid)

            if course_name in dept_courses.keys():
                teacher_ins = Instructor.objects.filter(mail=mail)
                course_ins = Course.objects.filter(course_id=course_name)
                ins= Teaches(mail=teacher_ins[0], course_id=course_ins[0])
                ins.save()


            else:
                course_id = request.POST['courseid']
                dept_courses = Course.objects.filter(dept_id = deptid)
                dept_ins = Department.objects.filter(dept_id = deptid)
            
            
                obj = Course.objects.filter(course_id=course_id, dept_id=dept_ins[0])
                # print(len(obj))

                if len(obj) == 0:
                    ins1 = Course(course_id=course_id, course_name=course_name, dept_id=dept_ins[0])
                    ins1.save()
                    teacher_ins = Instructor.objects.filter(mail=mail)
                    course_ins = Course.objects.filter(course_id=course_id)
                    ins2 = Teaches(mail=teacher_ins[0], course_id=course_ins[0])
                    ins2.save()
            return render(request, 'teacher_addcourses.html', {'courses':dept_courses})

    except Exception:
        print(Exception)
        return render(request, 'error.html')


def coursePage(request, variable):
    try:
        if variable == 'home':
            return redirect(login_to_home)
        elif variable == 'addcourse':
            return redirect(addcourse)
        elif variable == 'courses':
            return redirect(courses)

        elif variable == 'attendance':
            if request.method == 'GET':
                
                dept_id = request.session['deptidT']
                course_id = request.session['course_idT']
                dept_courses = get_depatment_courses(dept_id)
                course_name = dept_courses.get(course_id)
                name_attendance = get_attendance_register(course_id, dept_id)
                #print(name_attendance)

                
                dates = []
                for value in list(name_attendance.values())[0]:
                    dates.append(value[0])

                # Convert strings to date objects
                date_objects = [datetime.strptime(date, '%d-%m-%Y') for date in dates]

                # Sort the date objects
                sorted_dates = sorted(date_objects)

                # Convert back to strings if needed
                sorted_date_strings = [date.strftime('%d-%m-%Y') for date in sorted_dates]

                print(sorted_date_strings)
                dates = sorted_date_strings
                # Get week ranges
                week_ranges = get_week_ranges(dates)
                dates1=[]
                context_dates=[]
                # Check if a specific week is selected
                selected_week = request.GET.get('week')
                if selected_week:
                    
                    start_date, end_date = selected_week.split(' to ')
                    start_date_obj = datetime.strptime(start_date, '%d-%m-%Y')
                    end_date_obj = datetime.strptime(end_date, '%d-%m-%Y')
                    dates1 = [date for date in dates if start_date_obj <= datetime.strptime(date, '%d-%m-%Y') <= end_date_obj]
                    # Now filter the attendance records based on these dates
                    for name, att_list in name_attendance.items():
                        # Filter out records that are not within the selected week
                        filtered_att_list = [record for record in att_list if datetime.strptime(record[0], '%d-%m-%Y') >= start_date_obj and datetime.strptime(record[0], '%d-%m-%Y') <= end_date_obj]
                        name_attendance[name] = filtered_att_list
                    
                    context_dates = dates1
                else:
                    context_dates = dates
                
                

                # for name, att_list in name_attendance.items():
                    
                #     if len(att_list) != len(dates):
                #         name_attendance[name] = correct_attendance_list(name_attendance[name], context_dates)

                print(dates1)
                # context = {
                # 'name': course_name,
                # 'data': name_attendance,  # This should be filtered based on the selected week
                # 'dates': dates,
                # }
                context = {
                    'name': course_name,
                    'data': name_attendance,  # This should be filtered based on the selected week
                    'dates': context_dates,
                    'week_ranges': week_ranges,  # Add this to context
                    'selected_week': selected_week  # Add this to context
                }
                return render(request, 'attendanceregister.html', context)
            
                #return render(request, 'attendanceregister.html', {'name':course_name, 'data':name_attendance, 'dates':dates} )

            # if request.method == 'POST':
            #     date = request.POST['date']
            #     dept_id = request.session['deptidT']
            #     course_id = request.session['course_idT']
            #     dept_courses = get_depatment_courses(dept_id)
            #     course_name = dept_courses.get(course_id)
            #     result = get_attendance_register(course_id, date, dept_id)
            #     return render(request, 'attendanceregister.html', {'name':course_name, 'date':date, 'data':result} )
            

        elif variable == 'addstudents':
            return HttpResponse('<h2>Add Students</h2>')
            # if request.method == 'POST':
            #     form = TakesForm(request.POST)
            #     if form.is_valid():
            #         form.save()
            #         return HttpResponse('<h2>Student data added successfully!</h2>')
            #     else:
            #         return HttpResponse('<h2>Error adding student data</h2>')
            # else:
            #     form = TakesForm()
            #     return render(request, 'add_takes.html', {'form': form})
    


        elif variable == 'students':

            dept_id = request.session['deptidT']
            course_id = request.session['course_idT']
            print(dept_id,course_id)

            students = get_students_per_course(course_id, dept_id)
            
            print(students)

            # Get total classes for each student
            #total_classes = DailyAttendance.objects.filter(course_id=course_id).values('student_id').annotate(total=Count('date'))

            # Get attended classes for each student (where status is True)
            #attended_classes = DailyAttendance.objects.filter(course_id=course_id, status=True).values('student_id').annotate(attended=Count('date'))

            # Convert QuerySets to dictionaries for easier lookup
            #total_dict = {item['student_id']: item['total'] for item in total_classes}
            #attended_dict = {item['student_id']: item['attended'] for item in attended_classes}

            # Calculate attendance percentage
            # attendance_percentages = {}
            # for student_id, total in total_dict.items():
            #     attended = attended_dict.get(student_id, 0)
            #     percentage = (attended / total) * 100
            #     attendance_percentages[student_id] = percentage

            dept_courses = get_depatment_courses(dept_id)
            course_name = dept_courses.get(course_id)

            # context = {
            #     'name': course_name,
            #     'data': students,
            #     'attendance_percentages': attendance_percentages
            # }

            #return render(request, 'students.html', context)
            
            dept_id = request.session['deptidT']
            course_id = request.session['course_idT']
            print(dept_id)
            students = get_students_per_course(course_id, dept_id)
            print(students)
            dept_courses = get_depatment_courses(dept_id)
            course_name = dept_courses.get(course_id)
            return render(request, 'students.html',{'name':course_name, 'data':students} )

        elif variable == 'takeattendance':

            if request.method == 'GET':

                dept_id = request.session['deptidT']
                course_id = request.session['course_idT']
                dept_courses = get_depatment_courses(dept_id)
                course_name = dept_courses.get(course_id)
                return render(request, 'takeattendance.html', {'name': course_name})



            if request.method == 'POST' and 'photo' in request.FILES:

                dept_id = request.session['deptidT']
                course_id = request.session['course_idT']
                dept_courses = get_depatment_courses(dept_id)
                course_name = dept_courses.get(course_id)
                file = request.FILES['photo']
                
                # selected_date = request.POST.get('attendance_date')
                # # If you need to use selected_date as a datetime object, uncomment the following lines
                # try:
                #     selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                # except ValueError:
                #     # Handle the error or set a default date
                #     selected_date_obj = datetime.now().date()

                selected_date = request.POST.get('attendance_date')
                if not selected_date:  # Check if selected_date is empty
                    selected_date_obj = datetime.now().date()  # Use current date if empty
                else:
                    try:
                        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                    except ValueError:
                        selected_date_obj = datetime.now().date()  # Use current date if parsing fails

                photos = request.FILES.getlist('photo')
                #selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                print(selected_date,selected_date_obj)
                # Initialize a set to keep track of students marked present
                #students_marked_present = set()
                selected_date = selected_date_obj

                # Fetch all students for the course
                students = get_students_per_course(course_id, dept_id)

                # Initialize or update attendance records to Absent for all students
                for student in students:
                    student_id = student[1]
                    student_ins = Student.objects.get(student_id=student_id)
                    DailyAttendance.objects.update_or_create(
                        student_id=student_ins, 
                        course_id=Course.objects.get(course_id=course_id), 
                        date=selected_date, 
                        defaults={'status': False}
                    )

                for file in photos:
                    # ...[your existing code to handle each image and save path etc.]...
                    ext = file.name.split('.')[-1]
                    print("&&")
                    # temp = str(datetime.today()).split(':')
                    # folder_name = "%s_%s_%s_%s" % (dept_id, course_id, temp[0].replace(" ", "_"),temp[1])
                    folder_name = "%s_%s_%s" % (dept_id, course_id, selected_date)
                    image_save_path = os.path.join(MEDIA_ROOT, "attendance", folder_name)
                    print("&")
                    try:
                        os.makedirs(image_save_path,exist_ok=True)
                    except:
                        pass
                    # For each image process and mark attendance
                    print("****")
                    classroom_face_vectors = get_face_encodings(file, save_path=image_save_path)
                    
                    # ...[rest of your code for processing the face vectors and marking attendance]...
                    course_ins = Course.objects.filter(course_id=course_id)
                    date_obj = selected_date
                    students = get_students_per_course(course_id, dept_id)

                    student_ids = []
                    for student in students:
                        student_ids.append(student[1])
                        
                    num_students_in_course = len(student_ids)
                    number_faces_detected = len(classroom_face_vectors)
                    
                        
                    index_id = {}
                    scores_matrix = []
                    classroom_face_vectors = np.array(classroom_face_vectors)

                    print(student_ids)
                    

                    for i, id in enumerate(student_ids):
                        try:
                            f = open(MEDIA_ROOT + '/encodings/'+ id +'.pickle', 'rb')
                            student_face_vector = pkl.load(f)
                            f.close()
                            index_id[i] = id
                            #print(f'student_id:{id}')
                            print("Im hear ",id)
                            student_face_vector = np.squeeze(student_face_vector)  # shape becomes (512,)
                            #print("Before:", classroom_face_vectors.shape)
                            if classroom_face_vectors.shape[1] == 1:
                                classroom_face_vectors = np.squeeze(classroom_face_vectors, axis=1)

                            #print("After:", classroom_face_vectors.shape)

                            #classroom_face_vectors = np.squeeze(classroom_face_vectors, axis=1)  # shape becomes (1, 512)
                            #print(classroom_face_vectors.shape,"dsv",student_face_vector.shape)
                            scores = get_minimum_similiarity(student_face_vector, classroom_face_vectors)
                            print("BUG")
                            #print(scores,scores.shape)
                            scores_matrix.append(scores)

                            #print(index_id)
                            #print(scores_matrix.shape)

        
                        except Exception as e:
                            print(f"Error encountered: {e}")

                        #new 
                    scores_arr = np.array(scores_matrix)

                    #print(scores_arr)
                    # Initialize counters
                    count_present = 0
                    count_absent = 0

                    matched_detected_faces = set()

                    # Loop to check present students based on face similarity
                    for i, student_face_scores in enumerate(scores_arr):
                        max_sim_index = np.argmax(student_face_scores)
                        max_sim_value = student_face_scores[max_sim_index]

                        if max_sim_index in matched_detected_faces or max_sim_value <= sim_threshold:
                            continue

                        student_id = index_id[i]
                        student_ins = Student.objects.filter(student_id=student_id)
                        date_obj = selected_date
                        

                        existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

                        if max_sim_value > sim_threshold:
                            matched_detected_faces.add(max_sim_index)
                            if existing_attendance.exists():
                                existing_attendance.update(status=True)
                            else:
                                ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=True)
                                ins.save()
                            count_present += 1


                    # For students not detected
                    # For students not detected, mark them as absent
                    for student_id in set(index_id.values()) - set([index_id[i] for i in range(len(scores_arr)) if np.argmax(scores_arr[i]) in matched_detected_faces]):
                        student_ins = Student.objects.filter(student_id=student_id)
                        date_obj = selected_date
                        existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

                        if existing_attendance.exists():
                            existing_attendance.update(status=False)
                        else:
                            ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
                            ins.save()
                        #count_absent += 1

                    count_absent = num_students_in_course - count_present

                    data = [number_faces_detected, num_students_in_course, count_present, count_absent]
                    return render(request, 'take_attendance_message.html', {'name': course_name, 'data': data})
                
                        #print(scores_arr)
                    # assignments = hungarian_algorithm(scores_arr.copy())
                    #     # print(assignments)
                    # ans, ans_mat = ans_calculation(scores_arr, assignments)
                    # print(ans_mat)


                #     # Instead of immediately saving to the database, collect the student IDs marked as present
                #     for (row, col) in assignments:
                #         score = ans_mat[row][col]
                #         student_id = index_id.get(row)

                #         if score < sim_threshold:
                #             students_marked_present.add(student_id)

                # # Now, we mark the attendance for the entire list of students
                # course_ins = Course.objects.filter(course_id=course_id)
                # date_obj = datetime.now().date()
                # students = get_students_per_course(course_id, dept_id)

                # for student in students:
                #     student_id = student[1]
                #     status = student_id in students_marked_present  # True if present, otherwise False

                #     student_ins = Student.objects.filter(student_id=student_id)
                #     course_ins = Course.objects.filter(course_id=course_id)
                #     date_obj = datetime.now().date()

                #     # Check if attendance record already exists for the student, course, and date
                #     existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

                #     if existing_attendance.exists():
                #         # Update the existing record
                #         existing_attendance.update(status=status)
                #     else:
                #         # Create a new record
                #         ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=status)
                #         ins.save()

                # # for student in students:
                # #     student_id = student[1]
                # #     status = student_id in students_marked_present  # True if present, otherwise False

                # #     student_ins = Student.objects.filter(student_id=student_id)
                # #     ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=status)
                # #     ins.save()

                # # You can now calculate the number of present and absent students using the length of the students_marked_present set
                # num_students_in_course = len(students)
                # count_present = len(students_marked_present)
                # count_absent = num_students_in_course - count_present
                
                # data = [len(photos), num_students_in_course, count_present, count_absent]
                # return render(request, 'take_attendance_message.html',{'name':course_name, 'data':data})

            # if request.method == 'GET':
            #     dept_id = request.session['deptidT']
            #     course_id = request.session['course_idT']
            #     dept_courses = get_depatment_courses(dept_id)
            #     course_name = dept_courses.get(course_id)
            #     return render(request, 'takeattendance.html',{'name':course_name} )

            # if request.method == 'POST' and 'photo' in request.FILES:
            #     #folder='classroom_images/' 
            #     dept_id = request.session['deptidT']
            #     course_id = request.session['course_idT']
            #     dept_courses = get_depatment_courses(dept_id)
            #     course_name = dept_courses.get(course_id)

            #     file = request.FILES['photo']


            #     ext = file.name.split('.')[-1]
            #     temp = str(datetime.today()).split(':')
            #     folder_name = "%s_%s_%s_%s" % (dept_id, course_id, temp[0].replace(" ", "_"),temp[1])
            #     image_save_path = os.path.join(MEDIA_ROOT, "attendance", folder_name)

            #     try:
            #         os.mkdir(image_save_path)
            #     except:
            #         pass

            #     file_name = default_storage.save(os.path.join(image_save_path, 'classroom_image.'+ext), file)
            #     file = default_storage.open(file_name)
            #     # file_url = default_storage.url(file_name)
            #     # fs = FileSystemStorage(location=folder) 
            #     # filename = fs.save(file.name, file)
            #     # file = fs.open(filename)
            #     # file_url = fs.url(filename)
            #     classroom_face_vectors = get_face_encodings(file, save_path=image_save_path)
            #     #print(encoded_face_vectors)
            #     course_ins = Course.objects.filter(course_id=course_id)
            #     date_obj = datetime.now().date()
            #     students = get_students_per_course(course_id, dept_id)

            #     student_ids = []
            #     for student in students:
            #         student_ids.append(student[1])
                
            #     num_students_in_course = len(student_ids)
            #     number_faces_detected = len(classroom_face_vectors)
            #     cout_present = 0
            #     count_absent = 0
                
            #     index_id = {}
            #     scores_matrix = []

            #     for i, id in enumerate(student_ids):
            #         f = open(MEDIA_ROOT + '/encodings/'+ id +'.pickle', 'rb')
            #         student_face_vector = pkl.load(f)
            #         f.close()
            #         index_id[i] = id
            #         # print(f'student_id:{id}')

            #         scores = get_minimum_similiarity(student_face_vector, classroom_face_vectors)
            #         scores_matrix.append(scores)

            #     # print(index_id)
            #     #print(scores_matrix)

            #     #new 
            #     scores_arr = np.array(scores_matrix)
            #     #print(scores_arr)
            #     assignments = hungarian_algorithm(scores_arr.copy())
            #     # print(assignments)
            #     ans, ans_mat = ans_calculation(scores_arr, assignments)
            #     print(ans_mat)


            #     for (row, col) in assignments:
            #         score = ans_mat[row][col]
            #         student_id = index_id.get(row)
            #         del index_id[row]

            #         if score < sim_threshold:
            #             student_ins = Student.objects.filter(student_id=student_id)
            #             ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=True)
            #             ins.save()
            #             cout_present += 1
            #         else:
            #             student_ins = Student.objects.filter(student_id=student_id)
            #             ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
            #             ins.save()
            #             count_absent += 1

            #     # account for missing faces
            #     for student_id in index_id.values():
            #         student_ins = Student.objects.filter(student_id=student_id)
            #         ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
            #         ins.save()
            #         count_absent += 1

            #     data = [number_faces_detected, num_students_in_course, cout_present, count_absent]
            #     return render(request, 'take_attendance_message.html',{'name':course_name, 'data':data})

        elif variable == 'webcam_attendance':

            dept_id = request.session['deptidT']
            course_id = request.session['course_idT']
            dept_courses = get_depatment_courses(dept_id)
            course_name = dept_courses.get(course_id)
            #new
            # Initialize variables
            count = 0
            picture_interval = 90  # 2 minutes in seconds
            next_picture_time = time.time() + picture_interval
            max_pictures = 2

            cap = cv2.VideoCapture(0)
            while cap.isOpened():
                ret, frame = cap.read()
                cv2.imshow('Take Attendance', frame)

                key = cv2.waitKey(10) & 0xFF
                if key == ord('q'):
                    break

                if count < max_pictures and time.time() >= next_picture_time:
                    next_picture_time = time.time() + picture_interval

                    # Save the picture
                    timestamp = time.strftime('%Y%m%d%H%M%S')
                    picture_filename = f'{timestamp}.jpg'
                    temp = str(datetime.today()).split(':')
                    folder_name = "%s_%s_%s_%s" % (dept_id, course_id, temp[0].replace(" ", "_"), temp[1])
                    image_save_path = os.path.join(MEDIA_ROOT, "attendance", folder_name)

                    try:
                        os.mkdir(image_save_path)
                    except:
                        pass

                    cv2.imwrite(os.path.join(image_save_path, picture_filename), frame)
                    print(f'Picture taken and saved: {picture_filename}')
                    count += 1

                if count >= max_pictures:
                    break

            cap.release()
            cv2.destroyAllWindows()

            # file = frame.copy()
            
            temp = str(datetime.today()).split(':')
            folder_name = "%s_%s_%s_%s" % (dept_id, course_id, temp[0].replace(" ", "_"),temp[1])
            image_save_path = os.path.join(MEDIA_ROOT, "attendance", folder_name)

            try:
                os.mkdir(image_save_path)
            except:
                pass
           
            cv2.imwrite(image_save_path+'/classroom_image.jpg', frame)
            file = image_save_path+'/classroom_image.jpg'
            classroom_face_vectors = get_face_encodings(file, save_path=image_save_path)

            print(len(classroom_face_vectors))

            course_ins = Course.objects.filter(course_id=course_id)
            date_obj = datetime.now().date()
            students = get_students_per_course(course_id, dept_id)

            student_ids = []
            for student in students:
                student_ids.append(student[1])
                
            num_students_in_course = len(student_ids)
            number_faces_detected = len(classroom_face_vectors)
            cout_present = 0
            count_absent = 0
                
            index_id = {}
            scores_matrix = []

            for i, id in enumerate(student_ids):
                f = open(MEDIA_ROOT + '/encodings/'+ id +'.pickle', 'rb')
                student_face_vector = pkl.load(f)
                f.close()
                index_id[i] = id
                #print(f'student_id:{id}')
                print("Im hear")
                student_face_vector = np.squeeze(student_face_vector)  # shape becomes (512,)
                classroom_face_vectors = np.squeeze(classroom_face_vectors, axis=1)  # shape becomes (1, 512)


                scores = get_minimum_similiarity(student_face_vector, classroom_face_vectors)
                print('yes')
                scores_matrix.append(scores)

            #from sklearn.metrics.pairwise import cosine_similarity

            # ... [Your existing code up to the point where you've created scores_matrix]

            # Convert scores_matrix to a numpy array
            scores_arr = np.array(scores_matrix)
            print(scores_arr)
            # Initialize counters
            count_present = 0
            count_absent = 0

            matched_detected_faces = set()

            # Iterate over each registered student's face
            for i, student_face_scores in enumerate(scores_arr):
                # Get the index of the detected face with the highest similarity score for this registered face
                max_sim_index = np.argmax(student_face_scores)
                max_sim_value = student_face_scores[max_sim_index]

                # If this detected face is already matched, continue to the next registered face
                if max_sim_index in matched_detected_faces:
                    continue

                student_id = index_id[i]
                student_ins = Student.objects.filter(student_id=student_id)
                course_ins = Course.objects.filter(course_id=course_id)
                date_obj = datetime.now().date()

                # Check if attendance record already exists for the student, course, and date
                existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

                if max_sim_value > sim_threshold:
                    matched_detected_faces.add(max_sim_index)
                    if existing_attendance.exists():
                        existing_attendance.update(status=True)
                    else:
                        ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=True)
                        ins.save()
                    count_present += 1
                else:
                    if existing_attendance.exists():
                        existing_attendance.update(status=False)
                    else:
                        ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
                        ins.save()
                    count_absent += 1

            # For students not detected
            for student_id in set(index_id.values()) - set([index_id[i] for i in range(len(scores_arr)) if np.argmax(scores_arr[i]) in matched_detected_faces]):
                student_ins = Student.objects.filter(student_id=student_id)
                course_ins = Course.objects.filter(course_id=course_id)
                date_obj = datetime.now().date()

                existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

                if existing_attendance.exists():
                    existing_attendance.update(status=False)
                else:
                    ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
                    ins.save()
                count_absent += 1

            data = [number_faces_detected, num_students_in_course, count_present, count_absent]
            return render(request, 'take_attendance_message.html', {'name': course_name, 'data': data})


            # print(index_id)
            #print(scores_matrix)
            # scores_arr = np.array(scores_matrix)
            # # print(scores_arr)
            # assignments = hungarian_algorithm(scores_arr.copy())
            # #print(assignments)
            # ans, ans_mat = ans_calculation(scores_arr, assignments)
            # print(ans_mat)

            # for (row, col) in assignments:
            #     score = ans_mat[row][col]
            #     student_id = index_id.get(row)
            #     del index_id[row]

            #     student_ins = Student.objects.filter(student_id=student_id)
            #     course_ins = Course.objects.filter(course_id=course_id)
            #     date_obj = datetime.now().date()

            #     # Check if attendance record already exists for the student, course, and date
            #     existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

            #     if score < sim_threshold:
            #         if existing_attendance.exists():
            #             # Update the existing record
            #             existing_attendance.update(status=True)
            #         else:
            #             # Create a new record
            #             ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=True)
            #             ins.save()
            #         cout_present += 1
            #     else:
            #         if existing_attendance.exists():
            #             # Update the existing record
            #             existing_attendance.update(status=False)
            #         else:
            #             # Create a new record
            #             ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
            #             ins.save()
            #         count_absent += 1

            # # account for missing faces
            # for student_id in index_id.values():
            #     student_ins = Student.objects.filter(student_id=student_id)
            #     course_ins = Course.objects.filter(course_id=course_id)
            #     date_obj = datetime.now().date()

            #     # Check if attendance record already exists for the student, course, and date
            #     existing_attendance = DailyAttendance.objects.filter(student_id=student_ins[0], course_id=course_ins[0], date=date_obj)

            #     if existing_attendance.exists():
            #         # Update the existing record
            #         existing_attendance.update(status=False)
            #     else:
            #         # Create a new record
            #         ins = DailyAttendance(student_id=student_ins[0], course_id=course_ins[0], date=date_obj, status=False)
            #         ins.save()
            #     count_absent += 1


            # data = [number_faces_detected, num_students_in_course, cout_present, count_absent]
            # return render(request, 'take_attendance_message.html',{'name':course_name, 'data':data})

            # return render(request, 'error.html')
            

        else:
            dept_id = request.session['deptidT']
            dept_courses = get_depatment_courses(dept_id)
            if variable in dept_courses:
                request.session['course_idT'] = variable

            #dept_id = request.session['deptidT']
            #dept_courses = get_depatment_courses(dept_id)
            course_name = dept_courses.get(request.session['course_idT'])
            return render(request, 'teacher_coursepage.html', {'name':course_name})
    except Exception:
    
        print(Exception)
        return render(request, 'error.html')
    
def teacher_profile(request):
    print("yes")
    try:
        if request.method == 'POST':
            mail = request.POST['username']
            password = request.POST['password']

            user_data = Instructor.objects.get(mail=mail)
            deptname = Department.objects.get(dept_id=user_data.department)
            user = {'user':user_data, 'deptname':deptname, 'role':'teacher'}
            if user_data.password == password:
                print("yes1")
                request.session['usernameT'] = mail
                request.session['deptidT'] = user_data.department
                return render(request, 'home1.html', user)
            else:
                print("yes")
                return render(request, 'loginpage.html')

        if request.method == 'GET':
            if 'usernameT' in request.session:
                mail = request.session['usernameT']
                user_data = Instructor.objects.get(mail=mail)
                deptname = Department.objects.get(dept_id=user_data.department)
                user = {'user':user_data, 'deptname':deptname, 'role':'teacher'}
                print("yes1")
                return render(request, 'home1.html', user)
            else:
                print("yes2")
                
                return render(request, 'loginpage.html')
    except Exception:
        print(Exception)
        return render(request, 'error.html')
