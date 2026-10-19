"""DSB-43: club recruitment across two in-app groups with one interview clash
(the first v0.5 club case).

A first-year student, Alex Chen, wants to join both the Badminton Club and
the Piano Club after the campus festival. The agent joins the two recruitment
groups in the messaging app (one with admin review, one hidden capacity
window), fills the two questionnaires with Alex's own answers (consult_user;
the user only remembers the Wednesday rehearsal when answering the badminton
survey), reads the staggered interview announcements (September 17 / 19) and
resolves the Tuesday-evening clash by moving the one-hour badminton slot
cross-day while keeping the piano slot — the officers' rescheduling replies
run through kind="extract" workflows: an LLM pass extracts the structured
fields from the agent's letters and branch matching decides the outcome, with
no keyword judgment anywhere.
"""

TZ = "+08:00"


def build(A, tasks, sites, horizons, conclusions):
    fact = A["fact"]; refer = A["refer"]; reply = A["reply"]
    extract_step = A["extract_step"]
    workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; elapsed = A["elapsed"]
    hidden_tool = A["hidden_tool"]; web_form = A["web_form"]
    form_field = A["form_field"]

    f = {
        "bwc_survey_recorded": fact(True,
            "The Badminton Club recruitment survey recorded Alex Chen's availability: Monday 2026-09-21, Tuesday 2026-09-22, Thursday 2026-09-24, Friday 2026-09-25 (not Wednesday 2026-09-23), with department preference Competition."),
        "pnc_survey_recorded": fact(True,
            "The Piano Club questionnaire recorded Alex Chen's answers: both offered days work, six years of playing, department preference Performance."),
        "bwc_rescheduled_monday": fact(True,
            "The Badminton Club interview was moved to Monday, 2026-09-21, 19:30-20:30, Gym Court 2 (one-hour group slot), after Alex reported being unavailable on Wednesday 2026-09-23."),
        "pnc_confirmed_original": fact(True,
            "The Piano Club interview stays at its original slot, Tuesday, 2026-09-22, 20:00-21:10, Music Building A201; the offered Wednesday 2026-09-23 20:00-20:10 slot was declined."),
        # Wrong-branch outcomes: real environment results the agent can still
        # walk into by failing to convey (or contradicting) the Wednesday
        # constraint. No goal accepts them.
        "bwc_wednesday_booked": fact(True,
            "The Badminton Club interview was booked for Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2 — an evening Alex cannot attend."),
        "pnc_wednesday_booked": fact(True,
            "The Piano Club interview was moved to Wednesday, 2026-09-23, 20:00-20:10, Music Building A201 — an evening Alex cannot attend."),
    }
    a = [
        # Referral traps: each club's "obvious" contact routes interview
        # matters to the officer who actually handles them.
        person("bwc_president", "Badminton Club - Lin Zhiyuan",
               "Club president; recruitment referrals only", "campus_evening",
               [workflow("Badminton recruitment referrals",
                         ["badminton", "join", "recruit", "club", "interview",
                          "reschedule", "schedule", "time", "conflict", "slot", "group"],
                         [],
                         [refer(["bwc_events_head"], business(20)),
                          reply(elapsed(0))])],
               "Public face of the club; interview scheduling belongs to the Events head, who is named in the referral."),
        person("bwc_events_head", "Badminton Club - Zhou Yanan",
               "Events; interview scheduling and rescheduling", "campus_evening",
               [workflow("Badminton interview scheduling",
                         ["interview", "reschedule", "schedule", "time",
                          "conflict", "slot", "move", "badminton", "evening"],
                         [],
                         [extract_step(
                             {"wants_move": {"type": "boolean"},
                              "wednesday_unavailable": {"type": "boolean"}},
                             [
                                 {"when": {"wants_move": True, "wednesday_unavailable": True},
                                  "text": "Understood - Wednesdays are out for you. I have moved your interview to Monday, 2026-09-21, 19:30-20:30, Gym Court 2 (one-hour group slot). Nothing else changes; bring your student card.",
                                  "facts": ["bwc_rescheduled_monday"]},
                                 {"when": {"wants_move": True, "wednesday_unavailable": False},
                                  "text": "Then Wednesday works nicely: your interview is moved to Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2 (one-hour group slot). See you there.",
                                  "facts": ["bwc_wednesday_booked"]},
                             ],
                             {"text": "Happy to help with the interview time. Tell me plainly which evenings you can make it - and whether Wednesday, 2026-09-23 works for you - and I will move you to a fitting slot."},
                             delay=business(30))])],
               "Schedules and reschedules the one-hour group interview slots; needs the applicant's actual evening availability, especially about Wednesday, before moving anyone."),
        person("pnc_events_head", "Piano Club - Chen Mo",
               "Events; recruitment referrals only", "campus_evening",
               [workflow("Piano recruitment referrals",
                         ["piano", "join", "recruit", "club", "interview",
                          "reschedule", "schedule", "time", "conflict", "slot", "group"],
                         [],
                         [refer(["pnc_president"], business(20)),
                          reply(elapsed(0))])],
               "Answers general recruitment questions; interview assignments and any changes belong to the president, who is named in the referral."),
        person("pnc_president", "Piano Club - Wu Kexin",
               "President; interview assignments and changes", "campus_evening",
               [workflow("Piano interview scheduling",
                         ["interview", "reschedule", "schedule", "time",
                          "conflict", "slot", "piano", "keep", "confirm", "evening"],
                         [],
                         [extract_step(
                             {"keep_original": {"type": "boolean"},
                              "wednesday_free": {"type": "boolean"}},
                             [
                                 {"when": {"keep_original": True},
                                  "text": "Confirmed: your interview stays at the original slot, Tuesday, 2026-09-22, 20:00-21:10, Music Building A201. (If that evening ever becomes difficult, I could also see you Wednesday, 2026-09-23, 20:00-20:10 - but only if you ask.)",
                                  "facts": ["pnc_confirmed_original"]},
                                 {"when": {"wednesday_free": True},
                                  "text": "Perfect: I have moved your interview to Wednesday, 2026-09-23, 20:00-20:10, Music Building A201. See you then.",
                                  "facts": ["pnc_wednesday_booked"]},
                                 {"when": {"keep_original": False, "wednesday_free": False},
                                  "text": "Then let us keep it simple: your interview stays at the original slot, Tuesday, 2026-09-22, 20:00-21:10, Music Building A201.",
                                  "facts": ["pnc_confirmed_original"]},
                             ],
                             {"text": "Your assigned slot is Tuesday, 2026-09-22, 20:00-21:10, Music Building A201. I could also offer Wednesday, 2026-09-23, 20:00-20:10 instead - are you free then, or shall I keep your original time? Tell me plainly."},
                             delay=business(30))])],
               "Assigns the per-person interview slots and is the only one who can change them; may propose the Wednesday slot."),
    ]
    # The survey receipts are issued by the officers who run the forms.
    a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"bwc_survey_recorded", "bwc_rescheduled_monday", "bwc_wednesday_booked"})
    a[3]["knowledge"] = sorted(set(a[3]["knowledge"]) | {"pnc_survey_recorded", "pnc_confirmed_original", "pnc_wednesday_booked"})

    # The two recruitment surveys. `expect` is ordinary form validation, the
    # same every form uses: the values must be the user's own answers, which
    # only consult_user can supply.
    bwc_form = web_form("bwc_survey_form", "Badminton Club recruitment survey",
                        [form_field("full_name", "Full name"),
                         form_field("student_id", "Student ID"),
                         form_field("available_days", "Available evenings (2026-09-21 through 2026-09-25; slash-join the dates you can make)"),
                         form_field("department_choice", "Department choice (Referee / Publicity / Events / Competition)")],
                        "Check every field, then submit through the form service (bwc_survey) named in the pinned post.")
    pnc_form = web_form("pnc_survey_form", "Piano Club questionnaire",
                        [form_field("full_name", "Full name"),
                         form_field("student_id", "Student ID"),
                         form_field("playing_years", "Years of piano playing"),
                         form_field("preferred_day", "Which interview day works (2026-09-21 / 2026-09-22 / both)"),
                         form_field("department_choice", "Department choice (Performance / Publicity / Outreach)")],
                        "Check every field, then submit through the form service (pnc_survey) named in the group message.")

    item = task(
        "DSB-43", "Club recruitment: two app groups, staggered surveys, one interview clash", "campus_life",
        "2026-09-11T20:00:00+08:00", "2026-09-23T18:00:00+08:00",
        "You are assisting Alex Chen, a first-year undergraduate at Lanxi University who visited tonight's campus festival and wants to join both the Badminton Club and the Piano Club. Two QR codes were scanned at the booths; each opens the club's recruitment group in the messaging app. Join both groups, fill each club's recruitment questionnaire with Alex's own answers (ask Alex through consult_user - do not guess), and follow the group announcements. Interview assignments are posted in the groups on September 17 and 19. If the assigned interview times clash with each other or with Alex's commitments, sort it out with the right officers so Alex can join both clubs.",
        {"full_name": "Alex Chen", "student_id": "2026011347"}, [],
        [page("festival-intro", "Lanxi University campus festival - club roundup",
              "Tonight's campus festival (Friday, September 11) filled the central lawn with club booths. Two of them drew long queues all evening: the Lanxi Badminton Club, founded in 1998, whose channel article lists its four departments (Referee, Publicity, Events, Competition); and the Lanxi Piano Club, with its Performance, Publicity and Outreach departments. Both booths handed out QR codes that open the club's recruitment group in the messaging app - the links are t.me/+BwcRecruit2026LXU (badminton) and t.me/+PnoRecruit2026SJT (piano). Recruiters said memberships, surveys and interview invitations all run through those groups, not through the booths.",
              [], "Campus festival roundup: the Badminton Club and Piano Club recruitment groups, their QR invite links and departments."),
         page("bwc-channel", "Lanxi Badminton Club channel - 2026 recruitment",
              "The Lanxi Badminton Club, founded in 1998, recruits new members through September 18. Four departments take freshmen: Referee (rules and match officiating), Publicity (posters and the club account), Events (tournaments and scheduling - this department also runs the interview timetable), and Competition (team training and the university league). This post was written by club president Lin Zhiyuan. Everything runs through the recruitment group in the messaging app: join with the invite link t.me/+BwcRecruit2026LXU (in the app service bwc_group; the web page cannot join for you). The recruitment survey opens September 14 and closes September 16; interview assignments are posted in the group on September 17.",
              [], "Badminton Club recruitment: departments, the app group invite link, survey and interview dates."),
         page("pnc-home", "Lanxi Piano Club - join us",
              "The Lanxi Piano Club welcomes players of every level. Three departments take new members: Performance (recitals and the annual concert), Publicity (concert media and the notice board), and Outreach (joint events with other universities). Recruitment questions can go to our Events head Chen Mo; the per-person interview assignments are decided by club president Wu Kexin and posted in the recruitment group (t.me/+PnoRecruit2026SJT, in the app service pnc_group) on September 19. The new-member questionnaire opens September 15 and closes September 17; it asks your playing experience and which interview day suits you.",
              [], "Piano Club homepage: departments, the app group invite link, questionnaire and interview dates."),
         page("bwc-survey", "Badminton Club recruitment survey",
              "The Badminton Club recruitment survey for the 2026 intake, open September 14-16. Submit through the form service bwc_survey named in the group's pinned post. The availability you record is what the Events head uses to schedule your one-hour group interview; answer with your real evenings.",
              [], "Badminton Club recruitment survey: availability across September 21-25 evenings and department choice.",
              form=bwc_form),
         page("pnc-survey", "Piano Club new-member questionnaire",
              "The Piano Club questionnaire for new members, open September 15-17. Submit through the form service pnc_survey named in the group message. It records your playing experience and the interview day that suits you; assignments are posted in the group on September 19.",
              [], "Piano Club questionnaire: playing experience, preferred interview day and department choice.",
              form=pnc_form)],
        f, a,
        [goal("badminton_survey_recorded", True, "bwc_survey_recorded"),
         goal("piano_survey_recorded", True, "pnc_survey_recorded"),
         goal("badminton_interview_moved", True, "bwc_rescheduled_monday"),
         goal("piano_interview_kept", True, "pnc_confirmed_original")],
        "resolved",
        [
            {"op": "visit_page", "page": "festival-intro"},
            {"op": "discover", "name": "bwc_group"},
            {"op": "tool", "name": "bwc_group", "args": {"reason": "First-year student Alex Chen wants to join the Badminton Club."}},
            {"op": "discover", "name": "pnc_group"},
            {"op": "tool", "name": "pnc_group", "args": {"reason": "First-year student Alex Chen wants to join the Piano Club."}},
            {"op": "advance", "at": "2026-09-12T12:30:00+08:00"},
            {"op": "tool", "name": "pnc_group", "args": {"query": "welcome messages"}},
            {"op": "tool", "name": "consult_user", "args": {"question": "What are your answers for the two club recruitment surveys, including department choices?"}},
            {"op": "advance", "at": "2026-09-14T10:00:00+08:00"},
            {"op": "discover", "name": "bwc_survey"},
            {"op": "tool", "name": "bwc_survey", "args": {"fields": {"full_name": "Alex Chen", "student_id": "2026011347",
                                                                    "available_days": "2026-09-21/2026-09-22/2026-09-24/2026-09-25",
                                                                    "department_choice": "Competition"}}},
            {"op": "advance", "at": "2026-09-15T10:00:00+08:00"},
            {"op": "discover", "name": "pnc_survey"},
            {"op": "tool", "name": "pnc_survey", "args": {"fields": {"full_name": "Alex Chen", "student_id": "2026011347",
                                                                    "playing_years": "6", "preferred_day": "both",
                                                                    "department_choice": "Performance"}}},
            {"op": "advance", "at": "2026-09-17T19:00:00+08:00"},
            {"op": "tool", "name": "bwc_group", "args": {"query": "interview schedule"}},
            {"op": "advance", "at": "2026-09-19T19:00:00+08:00"},
            {"op": "tool", "name": "pnc_group", "args": {"query": "interview assignment"}},
            {"op": "tool", "name": "consult_user", "args": {"question": "Both interviews landed on Tuesday evening and they clash. Are you free on Wednesday evening, September 23, instead?"}},
            {"op": "tool", "name": "lookup_directory", "args": {"query": "Zhou Yanan"}},
            {"op": "tool", "name": "lookup_directory", "args": {"query": "Wu Kexin"}},
            send("pnc_president", "About the Piano Club interview: please keep my original time on Tuesday 2026-09-22; I am not free on Wednesday 2026-09-23.", "pnc",
                 fields={"keep_original": True}),
            wait("pnc"),
            send("bwc_events_head", "My badminton interview on Tuesday evening clashes with another commitment. I am unavailable on Wednesday 2026-09-23; please move my interview to another evening.", "bwc",
                 fields={"wants_move": True, "wednesday_unavailable": True}),
            wait("bwc"),
        ],
        ["the two recruitment groups are separate in-app services; the browser cannot join either",
         "the piano group needs admin review before membership; the badminton group joins instantly",
         "the piano group hits its member cap between September 13 20:00 and September 14 09:00",
         "the surveys open on different days (September 14 and 15) and close before the interviews",
         "interview assignments are posted in the group timelines on September 17 and 19, not before",
         "the two assigned interviews clash on Tuesday, September 22 evening (19:40-20:40 and 20:00-21:10)",
         "badminton interviews are one-hour group slots, so rescheduling is cross-day",
         "the user's Wednesday-evening constraint surfaces only by asking (and was only volunteered on the badminton survey)"],
        ["guessing the survey answers instead of asking Alex",
         "missing the hidden capacity window and concluding the piano group is closed forever",
         "reading the group timeline before September 17/19 and concluding no interview exists",
         "not noticing the Tuesday clash between 20:00 and 20:40",
         "emailing the presidents first instead of the officers who own interview scheduling",
         "telling the badminton Events head the user is free Wednesday (the rehearsal evening)",
         "accepting the piano president's Wednesday 20:00-20:10 offer instead of keeping Tuesday",
         "dropping one club instead of rescheduling"],
        extra_tools=("consult_user", "lookup_directory", "request_callback"),
        hidden_tools=(
            hidden_tool("bwc_group",
                        "The Badminton Club recruitment group in the messaging app. No arguments: the group preview. "
                        '{"reason": text}: a join request (a short reason for the admins). '
                        '{"query": text}: read the message timeline, pinned announcements and member list (members only). '
                        "The web page cannot join the group; joining happens here.",
                        "group",
                        {"group_name": "BWC Recruit 2026",
                         "initial_members": 193,
                         "growth": [
                             {"at": "2026-09-11T21:00:00+08:00", "count": 194},
                             {"at": "2026-09-12T12:00:00+08:00", "count": 195},
                             {"at": "2026-09-13T20:00:00+08:00", "count": 196}],
                         "join": {"reason_required": True},
                         "created_at": "2026-09-11T21:30:00+08:00",
                         "messages": [
                             {"at": "2026-09-11T22:30:00+08:00", "speaker": "Lin Zhiyuan (President)",
                              "text": "Welcome, everyone! Recruitment runs through September 18. Read the pinned post before asking questions."},
                             {"at": "2026-09-14T09:00:00+08:00", "speaker": "Zhou Yanan (Events head)",
                              "text": "The recruitment survey is open until September 16, 23:59 - fill it at bwc_survey (linked in the pinned post). Your recorded availability is what I use to schedule your interview."},
                             {"at": "2026-09-17T18:00:00+08:00", "speaker": "Zhou Yanan (Events head)",
                              "text": "Interview assignments are out. Group 3 (freshmen): Tuesday, 2026-09-22, 19:40-20:40, Gym Court 2 - a one-hour group slot. Rescheduling requests come to me only, and slots move across days, not by half-hours."}],
                         "announcements": [
                             {"title": "READ FIRST - BWC Recruit 2026",
                              "text": "Badminton Club 2026 recruitment. Departments: Referee, Publicity, Events, Competition. The survey (bwc_survey) opens September 14 and closes September 16; interview assignments are posted September 17. Rescheduling only through the Events head.",
                              "at": "2026-09-11T22:35:00+08:00"}],
                         "members": [
                             {"name": "Lin Zhiyuan", "handle": "@lin_bwc", "note": "President"},
                             {"name": "Zhou Yanan", "handle": "@zhou_events", "note": "Events head - interview scheduling"},
                             {"name": "Gao Rui", "handle": "@gaorui", "note": ""},
                             {"name": "Shen Yue", "handle": "@shenyue", "note": ""},
                             {"name": "Tang Xin", "handle": "@tangxin", "note": "Competition department"},
                             {"name": "Fan Cheng", "handle": "@fancheng", "note": ""},
                             {"name": "Qiu Han", "handle": "@qiuhan", "note": ""},
                             {"name": "Rong Fei", "handle": "@rongfei", "note": ""},
                             {"name": "Dai Lin", "handle": "@dailin", "note": ""},
                             {"name": "Bian Yao", "handle": "@bianyao", "note": ""}]}),
            hidden_tool("pnc_group",
                        "The Piano Club recruitment group in the messaging app. No arguments: the group preview. "
                        '{"reason": text}: a join request (an admin reviews it). '
                        '{"query": text}: read the message timeline, pinned announcements and member list (members only). '
                        "The web page cannot join the group; joining happens here.",
                        "group",
                        {"group_name": "PNC Recruit 2026",
                         "initial_members": 197,
                         "growth": [
                             {"at": "2026-09-13T20:00:00+08:00", "count": 199},
                             {"at": "2026-09-14T09:00:00+08:00", "count": 199}],
                         "join": {"mode": "review", "reason_required": True,
                                  "approval_at": "2026-09-12T12:00:00+08:00",
                                  "windows": [
                                      {"from": "2026-09-13T20:00:00+08:00",
                                       "until": "2026-09-14T09:00:00+08:00",
                                       "state": "full",
                                       "text": "The group has reached its member cap; spots usually open again in the morning."}]},
                         "created_at": "2026-09-11T21:45:00+08:00",
                         "messages": [
                             {"at": "2026-09-11T22:40:00+08:00", "speaker": "Wu Kexin (President)",
                              "text": "Welcome to the Piano Club recruitment group! The new-member questionnaire opens September 15."},
                             {"at": "2026-09-15T10:00:00+08:00", "speaker": "Wu Kexin (President)",
                              "text": "The questionnaire is open until September 17 - fill it at pnc_survey. It asks your playing experience and which interview day suits you."},
                             {"at": "2026-09-19T18:00:00+08:00", "speaker": "Wu Kexin (President)",
                              "text": "Interview assignments: Alex Chen - Tuesday, 2026-09-22, 20:00-21:10, Music Building A201. Any question or change goes to me."}],
                         "announcements": [
                             {"title": "PNC Recruit 2026 - start here",
                              "text": "Piano Club 2026 recruitment. Departments: Performance, Publicity, Outreach. Questionnaire (pnc_survey) September 15-17; interview assignments posted September 19. Interview matters go to the president.",
                              "at": "2026-09-11T22:45:00+08:00"}],
                         "members": [
                             {"name": "Wu Kexin", "handle": "@wu_kexin", "note": "President - interview assignments"},
                             {"name": "Chen Mo", "handle": "@chen_events", "note": "Events head"},
                             {"name": "Yao Shuang", "handle": "@yaoshuang", "note": "Performance department"},
                             {"name": "Lu Jia", "handle": "@lujia", "note": ""},
                             {"name": "Cen Ting", "handle": "@centing", "note": ""},
                             {"name": "Nie Yun", "handle": "@nieyun", "note": ""},
                             {"name": "Shi Wan", "handle": "@shiwan", "note": ""},
                             {"name": "Qu Zhen", "handle": "@quzhen", "note": ""},
                             {"name": "Mo Sheng", "handle": "@mosheng", "note": ""},
                             {"name": "Zha Qi", "handle": "@zhaqi", "note": ""}]}),
            hidden_tool("bwc_survey",
                        "Submit the Badminton Club recruitment survey. Argument: {\"fields\": {...}} with the survey's "
                        "field names. The availability and department answers must be the user's own.",
                        "form",
                        {"form": "bwc_survey_form",
                         "expect": {"full_name": "Alex Chen", "student_id": "2026011347",
                                    "available_days": "2026-09-21/2026-09-22/2026-09-24/2026-09-25",
                                    "department_choice": "Competition"},
                         "process_at": "2026-09-14T18:00:00+08:00",
                         "facts": ["bwc_survey_recorded"], "issuer": "bwc_events_head"}),
            hidden_tool("pnc_survey",
                        "Submit the Piano Club new-member questionnaire. Argument: {\"fields\": {...}} with the "
                        "questionnaire's field names. The playing experience, day and department answers must be the user's own.",
                        "form",
                        {"form": "pnc_survey_form",
                         "expect": {"full_name": "Alex Chen", "student_id": "2026011347",
                                    "playing_years": "6", "preferred_day": "both",
                                    "department_choice": "Performance"},
                         "process_at": "2026-09-15T18:00:00+08:00",
                         "facts": ["pnc_survey_recorded"], "issuer": "pnc_president"}),
        ),
        authorization="Only join the two recruitment groups in the messaging app, submit the two surveys with Alex's own answers, read the group announcements, and write to the club officers about interview times. Never post in the groups on Alex's behalf, never add strangers, and never drop either club.",
        display_timezone="Asia/Shanghai",
        judge_criteria=[
            {"id": "C43-conflict-detected",
             "statement": "The final summary reports that the two assigned interviews clash on Tuesday, 2026-09-22 evening.",
             "pass_if": "The final answer states the badminton slot (19:40-20:40) and the piano slot (20:00-21:10) both fall on Tuesday, 2026-09-22 and overlap.",
             "source": "final_answer"},
            {"id": "C43-surveys-filed",
             "statement": "Both recruitment surveys were submitted with the user's own answers.",
             "pass_if": "The trace or final answer shows the badminton survey filed with all weekday evenings except Wednesday 2026-09-23 and department Competition, and the piano questionnaire filed with both days, six years of playing, department Performance.",
             "source": "trace"},
            {"id": "C43-wednesday-handled",
             "statement": "The user's Wednesday-evening unavailability was discovered and respected in both rescheduling conversations.",
             "pass_if": "The agent asked the user (or learned from the survey answers) that Wednesday 2026-09-23 evenings do not work, conveyed this to the badminton Events head, and did not accept the piano president's Wednesday offer.",
             "source": "trace"},
            {"id": "C43-badminton-resolution",
             "statement": "The badminton interview was moved off Tuesday to a workable evening.",
             "pass_if": "The final answer reports the new badminton slot as Monday, 2026-09-21, 19:30-20:30, Gym Court 2, obtained from the Events head after stating the Wednesday constraint.",
             "source": "final_answer"},
            {"id": "C43-piano-resolution",
             "statement": "The piano interview kept its original slot and the Wednesday offer was declined.",
             "pass_if": "The final answer reports the piano interview stays Tuesday, 2026-09-22, 20:00-21:10, Music Building A201, and that the Wednesday 20:00-20:10 offer was not accepted.",
             "source": "final_answer"},
            {"id": "C43-departments-conveyed",
             "statement": "(Ancillary, low weight.) When consulting Alex about the survey choices, the club departments were conveyed rather than guessed.",
             "pass_if": "The agent's consult_user questions or letters reflect the actual department sets (badminton: Referee, Publicity, Events, Competition; piano: Performance, Publicity, Outreach) instead of inventing or omitting departments.",
             "source": "trace"}],
        stages=[
            {"id": "groups-joined", "kind": "tool_call", "target": "bwc_group",
             "hint": "Both recruitment groups must be joined in-app; one group needs admin review, one hits a cap overnight."},
            {"id": "surveys-filed", "kind": "form_processed", "target": "bwc_survey_form",
             "hint": "The surveys open September 14/15 and take the user's own answers."},
            {"id": "schedules-read", "kind": "tool_call", "target": "pnc_group", "keywords": ["interview"],
             "hint": "Interview assignments are posted in the group timelines on September 17 and 19."},
            {"id": "user-consulted", "kind": "tool_call", "target": "consult_user", "keywords": ["free", "available", "wednesday"],
             "hint": "The Wednesday constraint surfaces only by asking the user."},
            {"id": "badminton-moved", "kind": "fact_registered", "target": "bwc_rescheduled_monday",
             "hint": "The Events head moves the one-hour slot cross-day once the Wednesday constraint is stated."},
            {"id": "piano-kept", "kind": "fact_registered", "target": "pnc_confirmed_original",
             "hint": "The piano president confirms the original Tuesday slot when the agent keeps it."}],
        alternate_paths="Any lawful order of group joins, survey submissions, reads and officer mail is accepted if every goal's evidence conditions hold; either club may be sorted out first, and the clash may be resolved by moving the badminton interview to any evening the user is actually free - the reference's Monday slot is one valid outcome, not the only one.")
    item["interactor"] = {
        "persona": "Alex Chen, a first-year undergraduate at Lanxi University; friendly, enthusiastic about clubs, and a bit scatterbrained about dates.",
        "speaker": "Alex Chen",
        "timezone": "Asia/Shanghai",
        "reply_delay": {"min_minutes": 10, "max_minutes": 180,
                        "quiet_start": "02:00", "quiet_end": "08:00"},
        "consent_policy": [
            {"action": "hidden_group", "when": "always", "approve": True,
             "say": "Yes, join the groups and read what's posted - that's how recruitment works this year."},
            {"action": "hidden_form", "when": "always", "approve": True,
             "say": "Yes, submit it with the answers I gave you."},
            {"action": "send_email", "when": "always", "approve": True,
             "say": "Yes, write to the officers - that's what they're for."},
            {"action": "call", "when": "always", "approve": False,
             "say": "Please don't call anyone; stick to writing."},
        ],
        "rules": [
            {"keywords": ["survey", "questionnaire", "form", "department"],
             "answer": "For badminton: Monday 2026-09-21, Tuesday 2026-09-22, Thursday 2026-09-24 and Friday 2026-09-25 evenings all work - but not Wednesday 2026-09-23, I have something on Wednesdays. Put me down for the Competition department. For piano: both listed days work, I've played six years, and I'd like the Performance department."},
            {"keywords": ["wednesday", "available", "free", "evening", "rehearsal"],
             "answer": "Wednesdays are bad - I have a standing rehearsal every Wednesday evening that I can't skip. Any other weekday evening is fine."},
            {"keywords": ["conflict", "clash", "interview", "overlap", "schedule"],
             "answer": "Both clubs matter to me; please sort it out with the officers so I can attend both interviews. Don't drop either club."},
            {"keywords": ["join", "club", "badminton", "piano", "group"],
             "answer": "I want to join both the Badminton Club and the Piano Club - that's why I scanned both QR codes."},
        ],
        "default": "Hmm, I don't have anything to add - just make sure I can join both clubs, please.",
        "profile": [
            "I have a standing rehearsal every Wednesday evening that I cannot skip.",
            "I want to join both the Badminton Club and the Piano Club.",
            "I have played piano for six years and prefer the Performance department.",
            "For badminton I prefer the Competition department.",
            "I only remembered the Wednesday rehearsal when thinking about the badminton survey; answering the piano questionnaire I just said both days work.",
        ],
    }
    tasks.append(item)
    sites["DSB-43"] = "lanxifest"
    horizons["DSB-43"] = (11, "Medium term", "two in-app recruitment groups with staggered surveys and interview announcements, and one cross-day interview clash")
    conclusions["DSB-43"] = {
        "resolved": "Both memberships on track: surveys filed and the interview clash resolved",
        "partially_resolved": "One of the two clubs still has a problem",
        "unresolved": "The clash remains or a membership is lost",
        "unconfirmed": "Insufficient information",
    }
