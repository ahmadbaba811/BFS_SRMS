from flask import Flask, redirect, render_template, request, session, url_for
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash


DB_PATH = 'db/srms_db.db'


app = Flask(__name__)
app.secret_key = 'srms-development-key'

# @app.route("/")
# def home():
#     return "Hello world, from flask. My name is Ahmad"

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if session['user_type'] == 'Mentor':
        cursor.execute('SELECT Name, Email, Expertise FROM Mentor WHERE MentorID = ?', (session['person_id'],))
        profile = cursor.fetchone()
        
        cursor.execute('''
            SELECT DISTINCT Program.ProgramName, Program.StartDate, Program.EndDate
            FROM Program
            INNER JOIN Match ON Program.ProgramID = Match.ProgramID
            WHERE Match.MentorID = ?
            ORDER BY Program.StartDate ''', (session['person_id'], )
            )
        programs = cursor.fetchall()

        cursor.execute('''
            SELECT DISTINCT Mentee.Name, Mentee.Goal
            FROM Mentee
            INNER JOIN Match ON Mentee.MenteeID = Match.MenteeID
            WHERE Match.MentorID = ?
            ORDER BY Mentee.Name
        ''', (session['person_id'],))
        mentees = cursor.fetchall()

        cursor.execute('''
            SELECT Meeting.MeetingDate, Mentee.Name, Meeting.Notes
            FROM Meeting
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
            WHERE Match.MentorID = ?
            ORDER BY Meeting.MeetingDate DESC
        ''', (session['person_id'],))
        meetings = cursor.fetchall()

        template = 'mentor_dashboard.html'
    else:
        cursor.execute('SELECT Name, Email, Goal FROM Mentee WHERE MenteeID = ?', (session['person_id'],))
        profile = cursor.fetchone()

        cursor.execute('''
            SELECT DISTINCT Program.ProgramName, Program.StartDate, Program.EndDate
            FROM Program
            INNER JOIN Match ON Program.ProgramID = Match.ProgramID
            WHERE Match.MenteeID = ?
            ORDER BY Program.StartDate
        ''', (session['person_id'],))
        programs = cursor.fetchall()

        cursor.execute('''
            SELECT DISTINCT Mentor.Name, Mentor.Expertise
            FROM Mentor
            INNER JOIN Match ON Mentor.MentorID = Match.MentorID
            WHERE Match.MenteeID = ?
            ORDER BY Mentor.Name
        ''', (session['person_id'],))
        mentors = cursor.fetchall()

        cursor.execute('''
            SELECT Meeting.MeetingDate, Mentor.Name, Meeting.Notes
            FROM Meeting
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
            WHERE Match.MenteeID = ?
            ORDER BY Meeting.MeetingDate DESC
        ''', (session['person_id'],))
        meetings = cursor.fetchall()

        cursor.execute('''
            SELECT Meeting.MeetingDate, Mentor.Name, Meeting.Notes
            FROM Meeting
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
            WHERE Match.MenteeID = ? AND Meeting.MeetingDate >= date('now')
            ORDER BY Meeting.MeetingDate ASC
            LIMIT 1
        ''', (session['person_id'],))
        next_meeting = cursor.fetchone()

        cursor.execute('''
            SELECT AVG(Feedback.Rating), COUNT(Feedback.FeedbackID)
            FROM Feedback
            INNER JOIN Meeting ON Feedback.MeetingID = Meeting.MeetingID
            INNER JOIN Match ON Meeting.MatchID = Match.MatchID
            WHERE Match.MenteeID = ?
        ''', (session['person_id'],))
        feedback_summary = cursor.fetchone()

        cursor.execute('''
            SELECT AchievementType, Title, Organisation, AchievementDate
            FROM Achievement
            WHERE MenteeID = ?
            ORDER BY AchievementDate DESC
        ''', (session['person_id'],))
        achievements = cursor.fetchall()
        
        template = 'mentee_dashboard.html'

    conn.close()

    dashboard_data = {
        'user_name': session['user_name'],
        'profile': profile,
        'programs': programs,
        'meetings': meetings,
    }
    if session['user_type'] == 'Mentor':
        dashboard_data['mentees'] = mentees
    else:
        dashboard_data['mentors'] = mentors
        dashboard_data['achievements'] = achievements
        dashboard_data['next_meeting'] = next_meeting
        dashboard_data['feedback_summary'] = feedback_summary

    return render_template(template, **dashboard_data)

@app.route('/mentor_dashboard')
def mentor_dashboard():
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))
    return dashboard()

@app.route('/mentee_dashboard')
def mentee_dashboard():
    if session.get('user_type') != 'Mentee':
        return redirect(url_for('dashboard'))
    return dashboard()

@app.route('/programs')
def programs():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    programs = conn.execute('SELECT ProgramName, StartDate, EndDate FROM Program ORDER BY StartDate').fetchall()
    conn.close()
    return render_template('programs.html', programs=programs)

@app.route('/meetings')
def meetings():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    if session['user_type'] == 'Mentor':
        query = '''SELECT Meeting.MeetingDate, Mentee.Name, Meeting.Notes
                   FROM Meeting INNER JOIN Match ON Meeting.MatchID = Match.MatchID
                   INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
                   WHERE Match.MentorID = ? ORDER BY Meeting.MeetingDate DESC'''
    else:
        query = '''SELECT Meeting.MeetingDate, Mentor.Name, Meeting.Notes
                   FROM Meeting INNER JOIN Match ON Meeting.MatchID = Match.MatchID
                   INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
                   WHERE Match.MenteeID = ? ORDER BY Meeting.MeetingDate DESC'''
    meetings = conn.execute(query, (session['person_id'],)).fetchall()
    conn.close()
    return render_template('meetings.html', meetings=meetings, user_type=session['user_type'])

@app.route('/achievements')
def achievements():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    achievements = conn.execute('''
        SELECT AchievementType, Title, Organisation, AchievementDate
        FROM Achievement WHERE MenteeID = ? ORDER BY AchievementDate DESC
    ''', (session['person_id'],)).fetchall() if session['user_type'] == 'Mentee' else []
    conn.close()
    return render_template('achievements.html', achievements=achievements)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/students')
def students():
    return render_template('students.html')

@app.route('/teachers')
def teachers():
    return render_template('teachers.html')

@app.route('/subjects')
def subjects():
    return render_template('subjects.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # query_result = None
    # if request.method == 'POST':
    #     # run a sqlite3 query when the button is clicked
    #     conn = sqlite3.connect(DB_PATH)
    #     cursor = conn.cursor()
    #     cursor.execute('SELECT COUNT(*) FROM Login')
    #     ## [{id:1, regNo: 'U21AA1003', ....}, {}, {}]
    #     query_result = cursor.fetchone();
    #     for row in query_result:
    #         print(row);
  
    #     conn.close()

    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        # print(username, password)

        if not username or not password:
            error = 'Username and password are required.'
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''SELECT LoginID, Username, Password, UserType, MentorID, MenteeID FROM Login WHERE Username = ?''', (username,))
            account = cursor.fetchone();
            # print(account)

            if not account:
                error = 'Wrong username.'
            elif not account[2] != password:
            # elif not check_password_hash(account[2], password):
                error = 'Wrong password.'
            else:
                session['user_type'] = account[3]
                session['person_id'] = account[4] if account[3] == 'Mentor' else account[5]
                if account[3] == 'Mentor':
                    cursor.execute('SELECT Name FROM Mentor WHERE MentorID = ?', (session['person_id'],))
                else:
                    cursor.execute('SELECT Name FROM Mentee WHERE MenteeID = ?', (session['person_id'],))

                person = cursor.fetchone()
                # print(person, session['person_id'], account[3])
                
                session['user_name'] = person[0] if person else account[1]
                conn.close();
                
                destination = 'mentor_dashboard' if account[3] == 'Mentor' else 'mentee_dashboard'
                return redirect(url_for(destination))

            conn.close()
    
    return render_template('login.html', error=error)

# if __name__ == '__main__':
#     app.run(debug=True)