from datetime import date
import re
import sqlite3

from emailer import send_email
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


DB_PATH = 'db/srms_db.db'
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


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
    if session['user_type'] == 'SuperAdmin':
        return redirect(url_for('superadmin_dashboard'))

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

@app.route('/superadmin_dashboard')
def superadmin_dashboard():
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    counts = {
        'mentors': cursor.execute('SELECT COUNT(*) FROM Mentor').fetchone()[0],
        'mentees': cursor.execute('SELECT COUNT(*) FROM Mentee').fetchone()[0],
        'matches': cursor.execute('SELECT COUNT(*) FROM Match').fetchone()[0],
        'programs': cursor.execute('SELECT COUNT(*) FROM Program').fetchone()[0],
    }
    unmatched = cursor.execute('''
        SELECT Name, Email, Goal FROM Mentee
        WHERE MenteeID NOT IN (SELECT MenteeID FROM Match)
        ORDER BY Name
    ''').fetchall()
    recent_matches = cursor.execute('''
        SELECT Mentor.Name, Mentee.Name, Program.ProgramName, Match.MatchDate
        FROM Match
        INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
        INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
        INNER JOIN Program ON Match.ProgramID = Program.ProgramID
        ORDER BY Match.MatchID DESC LIMIT 5
    ''').fetchall()
    conn.close()

    return render_template('superadmin_dashboard.html', user_name=session['user_name'], counts=counts,
                           unmatched=unmatched, recent_matches=recent_matches)

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
    if session.get('user_type') not in ('Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    if session['user_type'] == 'Mentor':
        match_query = '''SELECT Match.MatchID, Mentee.Name, Program.ProgramName
                         FROM Match
                         INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
                         INNER JOIN Program ON Match.ProgramID = Program.ProgramID
                         WHERE Match.MentorID = ? ORDER BY Mentee.Name, Program.ProgramName'''
        meeting_query = '''SELECT Meeting.MeetingID, Meeting.MeetingDate, Mentee.Name, Meeting.Notes,
                                  Feedback.Rating, Feedback.Comments,
                                  CASE WHEN date(Meeting.MeetingDate) <= date('now') THEN 1 ELSE 0 END,
                                  CASE WHEN date(Meeting.MeetingDate) < date('now') OR Feedback.FeedbackID IS NOT NULL THEN 1 ELSE 0 END
                           FROM Meeting
                           INNER JOIN Match ON Meeting.MatchID = Match.MatchID
                           INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
                           LEFT JOIN Feedback ON Meeting.MeetingID = Feedback.MeetingID
                           WHERE Match.MentorID = ? ORDER BY Meeting.MeetingDate DESC'''
    else:
        match_query = '''SELECT Match.MatchID, Mentor.Name, Program.ProgramName
                         FROM Match
                         INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
                         INNER JOIN Program ON Match.ProgramID = Program.ProgramID
                         WHERE Match.MenteeID = ? ORDER BY Mentor.Name, Program.ProgramName'''
        meeting_query = '''SELECT Meeting.MeetingID, Meeting.MeetingDate, Mentor.Name, Meeting.Notes,
                                  Feedback.Rating, Feedback.Comments,
                                  CASE WHEN date(Meeting.MeetingDate) <= date('now') THEN 1 ELSE 0 END,
                                  CASE WHEN date(Meeting.MeetingDate) < date('now') OR Feedback.FeedbackID IS NOT NULL THEN 1 ELSE 0 END
                           FROM Meeting
                           INNER JOIN Match ON Meeting.MatchID = Match.MatchID
                           INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
                           LEFT JOIN Feedback ON Meeting.MeetingID = Feedback.MeetingID
                           WHERE Match.MenteeID = ? ORDER BY Meeting.MeetingDate DESC'''
    person_id = session['person_id']
    matches = conn.execute(match_query, (person_id,)).fetchall()
    meetings = conn.execute(meeting_query, (person_id,)).fetchall()
    edit_meeting_id = request.args.get('edit', type=int)
    if edit_meeting_id and not any(
        meeting[0] == edit_meeting_id and not meeting[7] for meeting in meetings
    ):
        edit_meeting_id = None
    conn.close()
    return render_template('meetings.html', meetings=meetings, matches=matches,
                           user_type=session['user_type'], edit_meeting_id=edit_meeting_id)

def notify_other_person(conn, match_id, action, meeting_date, notes, old_date=None):
    """Email the other person in the match about a scheduled or changed meeting."""
    row = conn.execute('''SELECT Mentor.Name, Mentor.Email, Mentee.Name, Mentee.Email
                          FROM Match
                          INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
                          INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
                          WHERE Match.MatchID = ?''', (match_id,)).fetchone()
    if not row:
        return False
    mentor_name, mentor_email, mentee_name, mentee_email = row
    if session['user_type'] == 'Mentor':
        recipient_name, recipient_email, sender_name = mentee_name, mentee_email, mentor_name
    else:
        recipient_name, recipient_email, sender_name = mentor_name, mentor_email, mentee_name

    if action == 'scheduled':
        subject = f'New meeting scheduled for {meeting_date}'
        details = f'{sender_name} has scheduled a meeting with you on {meeting_date}.'
    else:
        subject = f'Meeting updated: now {meeting_date}'
        details = f'{sender_name} has updated your meeting (previously {old_date}). It is now on {meeting_date}.'
    body = f'Hello {recipient_name},\n\n{details}\nNotes: {notes or "None"}\n\nSRMS Mentorship Platform'
    return send_email(recipient_email, subject, body)

@app.route('/meetings/add', methods=['POST'])
def add_meeting():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') not in ('Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))

    match_id = request.form.get('match_id', type=int)
    meeting_date = request.form.get('meeting_date', '').strip()
    notes = request.form.get('notes', '').strip()
    try:
        meeting_date = date.fromisoformat(meeting_date).isoformat()
    except ValueError:
        flash('Please enter a valid meeting date.', 'danger')
        return redirect(url_for('meetings'))

    if not match_id:
        flash('Please choose one of your mentorship matches.', 'danger')
        return redirect(url_for('meetings'))

    conn = sqlite3.connect(DB_PATH)
    if session['user_type'] == 'Mentor':
        match = conn.execute(
            'SELECT 1 FROM Match WHERE MatchID = ? AND MentorID = ?',
            (match_id, session['person_id'])
        ).fetchone()
    else:
        match = conn.execute(
            'SELECT 1 FROM Match WHERE MatchID = ? AND MenteeID = ?',
            (match_id, session['person_id'])
        ).fetchone()

    if not match:
        conn.close()
        flash('You can only add meetings for your own mentorship matches.', 'danger')
        return redirect(url_for('meetings'))

    conn.execute(
        'INSERT INTO Meeting (MatchID, MeetingDate, Notes) VALUES (?, ?, ?)',
        (match_id, meeting_date, notes)
    )
    conn.commit()
    emailed = notify_other_person(conn, match_id, 'scheduled', meeting_date, notes)
    conn.close()

    flash('Meeting added successfully.' + (' The other person was notified by email.' if emailed else ' (Email notification was not sent.)'), 'success')
    return redirect(url_for('meetings'))

@app.route('/meetings/<int:meeting_id>/edit', methods=['POST'])
def edit_meeting(meeting_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') not in ('Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))

    meeting_date = request.form.get('meeting_date', '').strip()
    notes = request.form.get('notes', '').strip()
    try:
        meeting_date = date.fromisoformat(meeting_date).isoformat()
    except ValueError:
        flash('Please enter a valid meeting date.', 'danger')
        return redirect(url_for('meetings', edit=meeting_id))

    person_column = 'MentorID' if session['user_type'] == 'Mentor' else 'MenteeID'
    conn = sqlite3.connect(DB_PATH)
    old = conn.execute('SELECT MatchID, MeetingDate FROM Meeting WHERE MeetingID = ?', (meeting_id,)).fetchone()
    cursor = conn.execute(f'''
        UPDATE Meeting
        SET MeetingDate = ?, Notes = ?
        WHERE MeetingID = ?
          AND date(MeetingDate) >= date('now')
          AND NOT EXISTS (SELECT 1 FROM Feedback WHERE Feedback.MeetingID = Meeting.MeetingID)
          AND date(?) >= date('now')
          AND MatchID IN (SELECT MatchID FROM Match WHERE {person_column} = ?)
    ''', (meeting_date, notes, meeting_id, meeting_date, session['person_id']))
    if cursor.rowcount == 0:
        conn.close()
        flash('Only upcoming meetings in your own matches can be edited, and the new date must be today or later.', 'danger')
        return redirect(url_for('meetings'))

    conn.commit()
    emailed = notify_other_person(conn, old[0], 'updated', meeting_date, notes, old[1])
    conn.close()
    flash('Meeting updated successfully.' + (' The other person was notified by email.' if emailed else ' (Email notification was not sent.)'), 'success')
    return redirect(url_for('meetings'))

@app.route('/meetings/<int:meeting_id>/delete', methods=['POST'])
def delete_meeting(meeting_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') not in ('Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))

    person_column = 'MentorID' if session['user_type'] == 'Mentor' else 'MenteeID'
    conn = sqlite3.connect(DB_PATH)
    conn.execute('BEGIN IMMEDIATE')
    meeting = conn.execute(f'''
        SELECT MeetingID FROM Meeting
        WHERE MeetingID = ?
          AND date(MeetingDate) >= date('now')
          AND NOT EXISTS (SELECT 1 FROM Feedback WHERE Feedback.MeetingID = Meeting.MeetingID)
          AND MatchID IN (SELECT MatchID FROM Match WHERE {person_column} = ?)
    ''', (meeting_id, session['person_id'])).fetchone()
    if not meeting:
        conn.close()
        flash('Only upcoming meetings in your own matches can be deleted.', 'danger')
        return redirect(url_for('meetings'))

    conn.execute('DELETE FROM Feedback WHERE MeetingID = ?', (meeting_id,))
    conn.execute('DELETE FROM Meeting WHERE MeetingID = ?', (meeting_id,))
    conn.commit()
    conn.close()
    flash('Meeting and its feedback deleted successfully.', 'success')
    return redirect(url_for('meetings'))

@app.route('/meetings/<int:meeting_id>/feedback', methods=['POST'])
def add_feedback(meeting_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') != 'Mentee':
        return redirect(url_for('dashboard'))

    rating = request.form.get('rating', type=int)
    comments = request.form.get('comments', '').strip()
    if rating not in range(1, 6):
        flash('Please choose a rating from 1 to 5.', 'danger')
        return redirect(url_for('meetings'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('BEGIN IMMEDIATE')
    meeting = conn.execute('''
        SELECT 1
        FROM Meeting
        INNER JOIN Match ON Meeting.MatchID = Match.MatchID
        WHERE Meeting.MeetingID = ? AND Match.MenteeID = ?
          AND date(Meeting.MeetingDate) <= date('now')
    ''', (meeting_id, session['person_id'])).fetchone()
    if not meeting:
        conn.close()
        flash('Feedback can only be submitted for your own completed meetings.', 'danger')
        return redirect(url_for('meetings'))

    existing_feedback = conn.execute(
        'SELECT 1 FROM Feedback WHERE MeetingID = ?', (meeting_id,)
    ).fetchone()
    if existing_feedback:
        conn.close()
        flash('Feedback has already been submitted for this meeting.', 'warning')
        return redirect(url_for('meetings'))

    conn.execute(
        'INSERT INTO Feedback (MeetingID, Rating, Comments) VALUES (?, ?, ?)',
        (meeting_id, rating, comments)
    )
    conn.commit()
    conn.close()

    flash('Feedback submitted successfully.', 'success')
    return redirect(url_for('meetings'))

@app.route('/achievements')
def achievements():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    user_type = session.get('user_type')
    if user_type not in ('Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))
    conn = sqlite3.connect(DB_PATH)
    # Verified: 0/NULL = pending, 1 = approved, 2 = rejected
    if user_type == 'Mentee':
        achievements = conn.execute('''
            SELECT Achievement.AchievementID, Achievement.AchievementType, Achievement.Title,
                   Achievement.Organisation, Achievement.AchievementDate,
                   COALESCE(Achievement.Verified, 0), Mentor.Name
            FROM Achievement LEFT JOIN Mentor ON Achievement.MentorID = Mentor.MentorID
            WHERE Achievement.MenteeID = ? ORDER BY Achievement.AchievementDate DESC
        ''', (session['person_id'],)).fetchall()
        people = conn.execute('''
            SELECT DISTINCT Mentor.MentorID, Mentor.Name FROM Match
            INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
            WHERE Match.MenteeID = ? ORDER BY Mentor.Name
        ''', (session['person_id'],)).fetchall()
    else:
        achievements = conn.execute('''
            SELECT Achievement.AchievementID, Achievement.AchievementType, Achievement.Title,
                   Achievement.Organisation, Achievement.AchievementDate,
                   COALESCE(Achievement.Verified, 0), Mentee.Name
            FROM Achievement INNER JOIN Mentee ON Achievement.MenteeID = Mentee.MenteeID
            WHERE Achievement.MentorID = ?
              AND Achievement.MenteeID IN (SELECT MenteeID FROM Match WHERE MentorID = ?)
            ORDER BY COALESCE(Achievement.Verified, 0) ASC, Achievement.AchievementDate DESC
        ''', (session['person_id'], session['person_id'])).fetchall()
        people = conn.execute('''
            SELECT DISTINCT Mentee.MenteeID, Mentee.Name FROM Match
            INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
            WHERE Match.MentorID = ? ORDER BY Mentee.Name
        ''', (session['person_id'],)).fetchall()
    conn.close()
    return render_template('achievements.html', achievements=achievements, people=people,
                           user_type=user_type, today=date.today().isoformat())

ACHIEVEMENT_TYPES = ['CV Job-Ready', 'First Job Application', 'First Interview', 'Job Offer',
                     'Job', 'Internship', 'Certification', 'Training', 'Project', 'Other']

@app.route('/achievements/add', methods=['POST'])
def add_achievement():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    user_type = session.get('user_type')
    if user_type not in ('Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))

    achievement_type = request.form.get('achievement_type', '').strip()
    title = request.form.get('title', '').strip()
    organisation = request.form.get('organisation', '').strip()
    achievement_date = request.form.get('achievement_date', '').strip()
    other_id = request.form.get('person_id', type=int)
    try:
        parsed_date = date.fromisoformat(achievement_date)
    except ValueError:
        parsed_date = None

    if achievement_type not in ACHIEVEMENT_TYPES or not title or not other_id or not parsed_date:
        flash('Please fill in the type, title, date and person.', 'danger')
        return redirect(url_for('achievements'))
    if parsed_date > date.today():
        flash('Achievement date cannot be in the future.', 'danger')
        return redirect(url_for('achievements'))

    if user_type == 'Mentee':
        mentee_id, mentor_id, verified = session['person_id'], other_id, 0
    else:
        mentee_id, mentor_id, verified = other_id, session['person_id'], 1

    conn = sqlite3.connect(DB_PATH)
    matched = conn.execute('SELECT 1 FROM Match WHERE MenteeID = ? AND MentorID = ?',
                           (mentee_id, mentor_id)).fetchone()
    if not matched:
        conn.close()
        flash('You can only record achievements for people you are matched with.', 'danger')
        return redirect(url_for('achievements'))
    conn.execute('''INSERT INTO Achievement
                    (MenteeID, MentorID, AchievementType, Title, Organisation, AchievementDate, Verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (mentee_id, mentor_id, achievement_type, title, organisation or None,
                  parsed_date.isoformat(), verified))
    conn.commit()
    conn.close()
    flash('Achievement recorded.' if verified else 'Achievement submitted for your mentor\'s approval.',
          'success')
    return redirect(url_for('achievements'))

@app.route('/achievements/<int:achievement_id>/review', methods=['POST'])
def review_achievement(achievement_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') != 'Mentor':
        return redirect(url_for('dashboard'))

    decision = request.form.get('decision')
    if decision not in ('approve', 'reject'):
        flash('Invalid decision.', 'danger')
        return redirect(url_for('achievements'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        'UPDATE Achievement SET Verified = ? WHERE AchievementID = ? AND MentorID = ?',
        (1 if decision == 'approve' else 2, achievement_id, session['person_id'])
    )
    conn.commit()
    conn.close()
    if cursor.rowcount:
        flash('Achievement %s.' % ('approved' if decision == 'approve' else 'rejected'), 'success')
    else:
        flash('Achievement not found.', 'danger')
    return redirect(url_for('achievements'))

@app.route('/mentees')
def mentees():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session['user_type'] != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    edit_id = request.args.get('edit')
    mentee_to_edit = None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MenteeID, Name, Email, Goal FROM Mentee ORDER BY Name')

    mentee_list = cursor.fetchall()

    if edit_id:
        cursor.execute('SELECT MenteeID, Name, Email, Goal FROM Mentee WHERE MenteeID = ?', (edit_id,))
        mentee_to_edit = cursor.fetchone()
        # fectchall = [{},{},{}]
        # fetchone = {}
    conn.close()

    return render_template('mentees.html', mentees=mentee_list, mentee_to_edit=mentee_to_edit)

@app.route('/mentees/add', methods=['POST'])
def add_mentee():
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '')
    email = request.form.get('email', '').strip()
    goal = request.form.get('goal', '') 

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentees'))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('mentees'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Mentee (Name, Email, Goal) VALUES (?, ?, ?)', (name, email, goal))
    conn.commit()
    conn.close()

    flash('Mentee added successfully.', 'success')
    return redirect(url_for('mentees'))

@app.route('/mentees/<int:mentee_id>/edit', methods=['POST'])
def edit_mentee(mentee_id):
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    goal = request.form.get('goal', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentees', edit=mentee_id))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('mentees', edit=mentee_id))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE Mentee SET Name = ?, Email = ?, Goal = ? WHERE MenteeID = ?', (name, email, goal, mentee_id))
    conn.commit()
    conn.close()

    flash('Mentee updated successfully.', 'success')
    return redirect(url_for('mentees'))

@app.route('/mentees/<int:mentee_id>/delete', methods=['POST'])
def delete_mentee(mentee_id):
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Match WHERE MenteeID = ?', (mentee_id,))
    cursor.execute('DELETE FROM Mentee WHERE MenteeID = ?', (mentee_id,))
    conn.commit()
    conn.close()

    flash('Mentee deleted successfully.', 'success')
    return redirect(url_for('mentees'))

@app.route('/mentors')
def mentors():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session['user_type'] != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    mentor_to_edit = None
    edit_id = request.args.get('edit')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MentorID, Name, Email, Expertise FROM Mentor ORDER BY Name')
    mentor_list = cursor.fetchall()

    if edit_id:
        cursor.execute('SELECT MentorID, Name, Email, Expertise FROM Mentor WHERE MentorID = ?', (edit_id,))
        mentor_to_edit = cursor.fetchone()
    conn.close()

    return render_template('mentors.html', mentors=mentor_list, mentor_to_edit=mentor_to_edit)

@app.route('/mentors/add', methods=['POST'])
def add_mentor():
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    expertise = request.form.get('expertise', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentors'))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('mentors'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT INTO Mentor (Name, Email, Expertise) VALUES (?, ?, ?)', (name, email, expertise))
    conn.commit()
    conn.close()

    flash('Mentor added successfully.', 'success')
    return redirect(url_for('mentors'))

@app.route('/mentors/<int:mentor_id>/edit', methods=['POST'])
def edit_mentor(mentor_id):
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    expertise = request.form.get('expertise', '').strip()

    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('mentors', edit=mentor_id))

    if not EMAIL_REGEX.match(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('mentors', edit=mentor_id))

    conn = sqlite3.connect(DB_PATH)
    conn.execute('UPDATE Mentor SET Name = ?, Email = ?, Expertise = ? WHERE MentorID = ?', (name, email, expertise, mentor_id))
    conn.commit()
    conn.close()

    flash('Mentor updated successfully.', 'success')
    return redirect(url_for('mentors'))

@app.route('/mentors/<int:mentor_id>/delete', methods=['POST'])
def delete_mentor(mentor_id):
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM Feedback
        WHERE MeetingID IN (
            SELECT MeetingID FROM Meeting
            WHERE MatchID IN (SELECT MatchID FROM Match WHERE MentorID = ?)
        )
    ''', (mentor_id,))
    cursor.execute('DELETE FROM Meeting WHERE MatchID IN (SELECT MatchID FROM Match WHERE MentorID = ?)', (mentor_id,))
    cursor.execute('DELETE FROM Match WHERE MentorID = ?', (mentor_id,))
    cursor.execute('DELETE FROM Achievement WHERE MentorID = ?', (mentor_id,))
    cursor.execute('DELETE FROM GroupMentor WHERE MentorID = ?', (mentor_id,))
    cursor.execute('DELETE FROM Recognition WHERE MentorID = ?', (mentor_id,))
    cursor.execute("DELETE FROM Login WHERE MentorID = ? AND UserType = 'Mentor'", (mentor_id,))
    cursor.execute('DELETE FROM Mentor WHERE MentorID = ?', (mentor_id,))
    conn.commit()
    conn.close()

    flash('Mentor deleted successfully.', 'success')
    return redirect(url_for('mentors'))

@app.route('/matches')
def matches():
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    mentee_rows = cursor.execute('SELECT MenteeID, Name, Email FROM Mentee ORDER BY Name').fetchall()
    match_rows = cursor.execute('''
        SELECT Match.MatchID, Mentor.MentorID, Mentor.Name, Mentee.MenteeID, Mentee.Name,
               Program.ProgramID, Program.ProgramName, Match.MatchDate
        FROM Match
        INNER JOIN Mentor ON Match.MentorID = Mentor.MentorID
        INNER JOIN Mentee ON Match.MenteeID = Mentee.MenteeID
        INNER JOIN Program ON Match.ProgramID = Program.ProgramID
        ORDER BY Match.MatchID DESC
    ''').fetchall()
    mentor_options = cursor.execute('SELECT MentorID, Name, Email FROM Mentor ORDER BY Name').fetchall()
    program_options = cursor.execute('SELECT ProgramID, ProgramName FROM Program ORDER BY StartDate').fetchall()

    match_to_edit = None
    edit_id = request.args.get('edit')
    if edit_id:
        cursor.execute('SELECT MatchID, MentorID, MenteeID, ProgramID FROM Match WHERE MatchID = ?', (edit_id,))
        match_to_edit = cursor.fetchone()
    conn.close()

    selected_mentee = match_to_edit[2] if match_to_edit else request.args.get('mentee', type=int)

    return render_template('matches.html', mentees=mentee_rows, matches=match_rows,
                           mentor_options=mentor_options, program_options=program_options,
                           match_to_edit=match_to_edit, selected_mentee=selected_mentee)

def read_match_form():
    # Returns (mentor_id, mentee_id, program_id) as ints, or None if invalid.
    try:
        mentor_id = int(request.form.get('mentor_id', ''))
        mentee_id = int(request.form.get('mentee_id', ''))
        program_id = int(request.form.get('program_id', ''))
    except ValueError:
        return None
    conn = sqlite3.connect(DB_PATH)
    valid = (
        conn.execute('SELECT 1 FROM Mentor WHERE MentorID = ?', (mentor_id,)).fetchone()
        and conn.execute('SELECT 1 FROM Mentee WHERE MenteeID = ?', (mentee_id,)).fetchone()
        and conn.execute('SELECT 1 FROM Program WHERE ProgramID = ?', (program_id,)).fetchone()
    )
    conn.close()
    return (mentor_id, mentee_id, program_id) if valid else None

@app.route('/matches/add', methods=['POST'])
def add_match():
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    data = read_match_form()
    if not data:
        flash('Please choose a valid mentor, mentee and program.', 'danger')
        return redirect(url_for('matches'))
    
    mentor_id, mentee_id, program_id = data

    conn = sqlite3.connect(DB_PATH)
    duplicate = conn.execute(
        'SELECT 1 FROM Match WHERE MentorID = ? AND MenteeID = ? AND ProgramID = ?',
        (mentor_id, mentee_id, program_id)).fetchone()
    if duplicate:
        conn.close()
        flash('That mentor is already matched to this mentee in this program.', 'danger')
        return redirect(url_for('matches'))

    conn.execute('INSERT INTO Match (ProgramID, MentorID, MenteeID) VALUES (?, ?, ?)', (program_id, mentor_id, mentee_id))
    conn.commit()
    conn.close()

    flash('Match created successfully.', 'success')
    return redirect(url_for('matches'))

@app.route('/matches/<int:match_id>/edit', methods=['POST'])
def edit_match(match_id):
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    data = read_match_form()
    if not data:
        flash('Please choose a valid mentor, mentee and program.', 'danger')
        return redirect(url_for('matches'))
    mentor_id, mentee_id, program_id = data

    conn = sqlite3.connect(DB_PATH)
    duplicate = conn.execute(
        'SELECT 1 FROM Match WHERE MentorID = ? AND MenteeID = ? AND ProgramID = ? AND MatchID != ?',
        (mentor_id, mentee_id, program_id, match_id)).fetchone()
    if duplicate:
        conn.close()
        flash('That match already exists.', 'danger')
        return redirect(url_for('matches'))

    conn.execute('UPDATE Match SET ProgramID = ?, MentorID = ?, MenteeID = ? WHERE MatchID = ?',
                 (program_id, mentor_id, mentee_id, match_id))
    conn.commit()
    conn.close()

    flash('Match updated successfully.', 'success')
    return redirect(url_for('matches'))

@app.route('/matches/<int:match_id>/delete', methods=['POST'])
def delete_match(match_id):
    if session.get('user_type') != 'SuperAdmin':
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Meetings and feedback belong to a match, so remove them first
    cursor.execute('DELETE FROM Feedback WHERE MeetingID IN (SELECT MeetingID FROM Meeting WHERE MatchID = ?)', (match_id,))
    cursor.execute('DELETE FROM Meeting WHERE MatchID = ?', (match_id,))
    cursor.execute('DELETE FROM Match WHERE MatchID = ?', (match_id,))
    conn.commit()
    conn.close()

    flash('Match removed successfully.', 'success')
    return redirect(url_for('matches'))

# Searchable record types. Each "scope" limits what a Mentor / Mentee may see;
# SuperAdmin sees everything. The first column is the link text on the results page.
_MENTOR_MENTEES = 'SELECT MenteeID FROM Match WHERE MentorID = :pid'
_MENTEE_MENTORS = 'SELECT MentorID FROM Match WHERE MenteeID = :pid'
_MATCH_SCOPE = {'Mentor': 'x.MentorID = :pid', 'Mentee': 'x.MenteeID = :pid'}
_MEETING_JOINS = ('LEFT JOIN Match x ON t.MatchID = x.MatchID '
                  'LEFT JOIN Mentor mr ON x.MentorID = mr.MentorID '
                  'LEFT JOIN Mentee me ON x.MenteeID = me.MenteeID')
SEARCH_SPECS = [
    {'key': 'program', 'title': 'Programs', 'id': 'p.ProgramID', 'from': 'Program p',
     'columns': [('Program', 'p.ProgramName'), ('Start date', 'p.StartDate'), ('End date', 'p.EndDate')],
     'scope': {'Mentor': 'p.ProgramID IN (SELECT ProgramID FROM Match WHERE MentorID = :pid)',
               'Mentee': 'p.ProgramID IN (SELECT ProgramID FROM Match WHERE MenteeID = :pid)'}},
    {'key': 'mentor', 'title': 'Mentors', 'id': 'm.MentorID', 'from': 'Mentor m',
     'columns': [('Name', 'm.Name'), ('Email', 'm.Email'), ('Expertise', 'm.Expertise'),
                 ('Joined', 'm.JoinedAt')],
     'scope': {'Mentor': 'm.MentorID = :pid', 'Mentee': 'm.MentorID IN (%s)' % _MENTEE_MENTORS}},
    {'key': 'mentee', 'title': 'Mentees', 'id': 'e.MenteeID', 'from': 'Mentee e',
     'columns': [('Name', 'e.Name'), ('Email', 'e.Email'), ('Goal', 'e.Goal'), ('Joined', 'e.JoinedAt')],
     'scope': {'Mentor': 'e.MenteeID IN (%s)' % _MENTOR_MENTEES, 'Mentee': 'e.MenteeID = :pid'}},
    {'key': 'match', 'title': 'Matches', 'id': 'x.MatchID',
     'from': ('Match x LEFT JOIN Mentor mr ON x.MentorID = mr.MentorID '
              'LEFT JOIN Mentee me ON x.MenteeID = me.MenteeID '
              'LEFT JOIN Program p ON x.ProgramID = p.ProgramID'),
     'columns': [('Mentor', 'mr.Name'), ('Mentee', 'me.Name'), ('Program', 'p.ProgramName'),
                 ('Matched on', 'x.MatchDate')],
     'scope': _MATCH_SCOPE},
    {'key': 'meeting', 'title': 'Meetings', 'id': 't.MeetingID', 'from': 'Meeting t ' + _MEETING_JOINS,
     'columns': [('Date', 't.MeetingDate'), ('Mentor', 'mr.Name'), ('Mentee', 'me.Name'),
                 ('Notes', 't.Notes')],
     'scope': _MATCH_SCOPE},
    {'key': 'feedback', 'title': 'Feedback', 'id': 'f.FeedbackID',
     'from': 'Feedback f LEFT JOIN Meeting t ON f.MeetingID = t.MeetingID ' + _MEETING_JOINS,
     'columns': [('Meeting date', 't.MeetingDate'), ('Mentor', 'mr.Name'), ('Mentee', 'me.Name'),
                 ('Rating', 'f.Rating'), ('Comments', 'f.Comments'), ('Submitted', 'f.SubmittedAt')],
     'scope': _MATCH_SCOPE},
    {'key': 'achievement', 'title': 'Achievements', 'id': 'a.AchievementID',
     'from': ('Achievement a LEFT JOIN Mentee me ON a.MenteeID = me.MenteeID '
              'LEFT JOIN Mentor mr ON a.MentorID = mr.MentorID'),
     'columns': [('Title', 'a.Title'), ('Type', 'a.AchievementType'), ('Mentee', 'me.Name'),
                 ('Mentor', 'mr.Name'), ('Organisation', 'a.Organisation'), ('Date', 'a.AchievementDate'),
                 ('Status', "CASE COALESCE(a.Verified, 0) WHEN 1 THEN 'Approved' "
                            "WHEN 2 THEN 'Rejected' ELSE 'Pending' END")],
     'scope': {'Mentor': 'a.MentorID = :pid', 'Mentee': 'a.MenteeID = :pid'}},
    {'key': 'group', 'title': 'Mentorship groups', 'id': 'g.GroupID',
     'from': 'MentorshipGroup g LEFT JOIN Program p ON g.ProgramID = p.ProgramID',
     'columns': [('Group', 'g.GroupName'), ('Program', 'p.ProgramName'), ('Created', 'g.CreatedAt')],
     'scope': {'Mentor': 'g.GroupID IN (SELECT GroupID FROM GroupMentor WHERE MentorID = :pid)',
               'Mentee': 'g.GroupID IN (SELECT GroupID FROM GroupMentee WHERE MenteeID = :pid)'}},
    {'key': 'recognition', 'title': 'Recognitions', 'id': 'r.RecognitionID',
     'from': ('Recognition r LEFT JOIN Mentor mr ON r.MentorID = mr.MentorID '
              'LEFT JOIN Mentee me ON r.MenteeID = me.MenteeID '
              'LEFT JOIN Program p ON r.ProgramID = p.ProgramID'),
     'columns': [('Type', 'r.RecognitionType'), ('Mentor', 'mr.Name'), ('Mentee', 'me.Name'),
                 ('Program', 'p.ProgramName'), ('Month', 'r.Month'), ('Reason', 'r.Reason')],
     'scope': {'Mentor': 'r.MentorID = :pid OR r.MenteeID IN (%s)' % _MENTOR_MENTEES,
               'Mentee': 'r.MenteeID = :pid OR r.MentorID IN (%s)' % _MENTEE_MENTORS}},
]
SEARCH_SPECS_BY_KEY = {spec['key']: spec for spec in SEARCH_SPECS}
SEARCH_LIMIT = 50

def scope_clause(spec):
    """SQL condition restricting a record type to what the current user may see."""
    if session['user_type'] == 'SuperAdmin':
        return '1 = 1'
    return '(%s)' % spec['scope'][session['user_type']]

@app.route('/search')
def search():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') not in ('SuperAdmin', 'Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))

    term = request.args.get('q', '').strip()
    sections = []
    if term:
        like = '%' + term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        conn = sqlite3.connect(DB_PATH)
        for spec in SEARCH_SPECS:
            select_cols = ', '.join(expr for _, expr in spec['columns'])
            match_sql = ' OR '.join("COALESCE(CAST(%s AS TEXT), '') LIKE :q ESCAPE '\\'" % expr
                                    for _, expr in spec['columns'])
            rows = conn.execute(
                'SELECT %s, %s FROM %s WHERE (%s) AND %s ORDER BY %s DESC LIMIT %d' % (
                    spec['id'], select_cols, spec['from'], match_sql, scope_clause(spec),
                    spec['id'], SEARCH_LIMIT),
                {'q': like, 'pid': session['person_id']}
            ).fetchall()
            if rows:
                sections.append({'key': spec['key'], 'title': spec['title'],
                                 'headers': [label for label, _ in spec['columns']], 'rows': rows,
                                 'limited': len(rows) == SEARCH_LIMIT})
        conn.close()
    return render_template('search.html', term=term, sections=sections,
                           total=sum(len(s['rows']) for s in sections))

@app.route('/record/<key>/<int:record_id>')
def record_detail(key, record_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') not in ('SuperAdmin', 'Mentor', 'Mentee'):
        return redirect(url_for('dashboard'))
    spec = SEARCH_SPECS_BY_KEY.get(key)
    if not spec:
        flash('Unknown record type.', 'danger')
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT %s FROM %s WHERE %s = :id AND %s' % (
            ', '.join(expr for _, expr in spec['columns']), spec['from'], spec['id'], scope_clause(spec)),
        {'id': record_id, 'pid': session['person_id']}
    ).fetchone()
    conn.close()
    if not row:
        flash('That record was not found.', 'danger')
        return redirect(url_for('dashboard'))

    fields = [(label, value) for (label, _), value in zip(spec['columns'], row)]
    return render_template('record_detail.html', spec_title=spec['title'], fields=fields,
                           heading=row[0] or '%s #%d' % (spec['title'], record_id))

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
            elif not check_password_hash(account[2], password):
                error = 'Wrong password.'
            else:
                session['user_type'] = account[3]
                session['person_id'] = account[4] if account[3] in ('Mentor', 'SuperAdmin') else account[5]
                if account[3] in ('Mentor', 'SuperAdmin'):
                    cursor.execute('SELECT Name FROM Mentor WHERE MentorID = ?', (session['person_id'],))
                else:
                    cursor.execute('SELECT Name FROM Mentee WHERE MenteeID = ?', (session['person_id'],))

                person = cursor.fetchone()
                # print(person, session['person_id'], account[3])
                
                session['user_name'] = person[0] if person else account[1]
                conn.close();
                
                if account[3] == 'SuperAdmin':
                    return redirect(url_for('superadmin_dashboard'))
                elif account[3] == 'Mentor':
                    return redirect(url_for('mentor_dashboard'))
                else:
                    return redirect(url_for('mentee_dashboard'))

            conn.close()
    
    return render_template('login.html', error=error)

# if __name__ == '__main__':
#     app.run(debug=True)