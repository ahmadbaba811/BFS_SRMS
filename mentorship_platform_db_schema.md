**-- Mentorship Program — Beginner SQLite Model (v2)**

\-- 10 tables: Program, Mentor, Mentee, Match, Meeting, Feedback, Achievement



\-- Program: a mentorship program mentors/mentees belong to

CREATE TABLE Program (

&#x20;   ProgramID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   ProgramName TEXT,

&#x20;   StartDate TEXT,

&#x20;   EndDate TEXT

);



\-- Mentor: a person offering mentorship

CREATE TABLE Mentor (

&#x20;   MentorID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   Name TEXT,

&#x20;   Email TEXT,

&#x20;   Expertise TEXT,

&#x20;   JoinedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);



\-- Mentee: a person receiving mentorship

CREATE TABLE Mentee (

&#x20;   MenteeID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   Name TEXT,

&#x20;   Email TEXT,

&#x20;   Goal TEXT,

&#x20;   JoinedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);



\-- Match: pairs a mentor with a mentee in a program (1-to-1 mentorship)

CREATE TABLE Match (

&#x20;   MatchID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   ProgramID INTEGER,

&#x20;   MentorID INTEGER,

&#x20;   MenteeID INTEGER,

&#x20;   MatchDate TEXT DEFAULT CURRENT\_TIMESTAMP

);



\-- Meeting: a single mentoring session between a matched pair

CREATE TABLE Meeting (

&#x20;   MeetingID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   MatchID INTEGER,

&#x20;   MeetingDate TEXT,

&#x20;   Notes TEXT

);



\-- Feedback: rating/comments left about a meeting

CREATE TABLE Feedback (

&#x20;   FeedbackID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   MeetingID INTEGER,

&#x20;   Rating INTEGER,

&#x20;   Comments TEXT,

&#x20;   SubmittedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);



\-- MentorshipGroup: a group mentorship track (up to 3 mentors, many mentees)

CREATE TABLE MentorshipGroup (

&#x20;   GroupID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   ProgramID INTEGER,

&#x20;   GroupName TEXT,

&#x20;   CreatedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);



\-- GroupMentor: mentors assigned to a group (app enforces max 3 per group)

CREATE TABLE GroupMentor (

&#x20;   GroupID INTEGER,

&#x20;   MentorID INTEGER,

&#x20;   PRIMARY KEY (GroupID, MentorID)

);



\-- GroupMentee: mentees who are members of a group

CREATE TABLE GroupMentee (

&#x20;   GroupID INTEGER,

&#x20;   MenteeID INTEGER,

&#x20;   PRIMARY KEY (GroupID, MenteeID)

);



\-- Recognition: Mentor/Mentee of the Month award

CREATE TABLE Recognition (

&#x20;   RecognitionID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   ProgramID INTEGER,

&#x20;   RecognitionType TEXT,   -- 'Mentor of the Month' or 'Mentee of the Month'

&#x20;   MentorID INTEGER,       -- filled when RecognitionType is for a mentor

&#x20;   MenteeID INTEGER,       -- filled when RecognitionType is for a mentee

&#x20;   Month TEXT,             -- e.g. '2026-08'

&#x20;   Reason TEXT,

&#x20;   AwardedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);



\-- Login: simple account for a mentor or mentee to sign in

CREATE TABLE Login (

&#x20;   LoginID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   Username TEXT,

&#x20;   Password TEXT,

&#x20;   UserType TEXT,   -- 'Mentor' or 'Mentee'

&#x20;   MentorID INTEGER,

&#x20;   MenteeID INTEGER,

&#x20;   CreatedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);





\-- Achievement: an outcome recorded for a mentee (e.g. got a job, finished a training)

CREATE TABLE Achievement (

&#x20;   AchievementID INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20;   MenteeID INTEGER,

&#x20;   MentorID INTEGER,       -- mentor who contributed to this achievement

&#x20;   AchievementType TEXT,   -- e.g. 'Job', 'Internship', 'Certification', 'Training'

&#x20;   Title TEXT,

&#x20;   Organisation TEXT,

&#x20;   AchievementDate TEXT,

&#x20;   Verified INTEGER,

&#x20;   CreatedAt TEXT DEFAULT CURRENT\_TIMESTAMP

);

