from connect import run_query


tutors = run_query("SELECT * FROM tutors")

#print(tutors)     

"""
tutors[0]

{
 'tpid': '6235552',
 'tlname': 'Penate', 
 'tfname': 'Robert', 
 'ttimes':  [
                'Monday 12pm-2pm',
                'Wednesday 10am-2pm'
            ]
}
"""

tutorTimes = []
for item in tutors:
    for time in item['ttimes']:
        tutorTimes.append((item['tfname'], time)) 

print(tutorTimes)
