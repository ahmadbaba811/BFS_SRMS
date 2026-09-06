from flask import Flask, redirect, render_template, request, session, url_for
import sqlite3


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
    print(session['user_type'], session['person_id'])
    if session['user_type'] == 'Mentor':
        cursor.execute('''
            SELECT Program.ProgramName, Program.StartDate, Program.EndDate
            FROM Program
            INNER JOIN Match ON Program.ProgramID = Match.ProgramID
            WHERE Match.MentorID = ?
        ''', (session['person_id'],))
    else:
        cursor.execute('''
            SELECT Program.ProgramName, Program.StartDate, Program.EndDate
            FROM Program
            INNER JOIN Match ON Program.ProgramID = Match.ProgramID
            WHERE Match.MenteeID = ?
        ''', (session['person_id'],))

    programs = cursor.fetchall()
    print(programs)
    conn.close()

    return render_template('home.html', user_name=session['user_name'], programs=programs)

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
            elif account[2] != password:
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
                conn.close()
                return redirect(url_for('dashboard'))

            conn.close()
    
    return render_template('login.html', error=error)

# if __name__ == '__main__':
#     app.run(debug=True)