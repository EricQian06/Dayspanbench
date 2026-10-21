"""DSB-43: club recruitment across two in-app groups with one interview clash
(the first v0.5 club case, rewritten on the v0.6 world-graph model).

A first-year student, Alex Chen, wants to join both the Badminton Club and
the Piano Club after the campus festival. The agent joins the two recruitment
groups in the messaging app (one with admin review, one hidden capacity
window), fills the two questionnaires with Alex's own answers (consult_user;
the user only remembers the Wednesday rehearsal when answering the badminton
survey), reads the staggered interview announcements (September 17 / 19) and
resolves the Tuesday-evening clash by moving the one-hour badminton slot
cross-day while keeping the piano slot.

Graph model (docs/graph-workflow-redesign.md): the workflow/extract_step
authoring is gone. Each NPC owns graph nodes; the rescheduling conversations
are evidence-driven: the badminton side is a three-stage flow (a service
node that proposes an evening, a self-loop confirmation node negotiating
with the agent, and a swap-check node where the Events head asks the target
day's students — Monday always fails there and loops back into the
confirmation conversation with the next evening, a successful swap settles
terminally and closes the negotiation), while the piano
side is a single service node. The club presidents' referrals are self-loop
inquiry nodes (volatile `user_inquired` evidence clears after each answer),
and the survey/announcement milestones are environment nodes backfilled by
form-processing and scheduled events.
"""

TZ = "+08:00"


def _inquiry(node_id, owner, title, reply_text, contacts=(), on_completed=None,
             delay_minutes=20, calendar="campus_evening"):
    """A self-loop answerable node: volatile `user_inquired` evidence, one
    canonical answer, contact sharing as an effect, reset after each fire.
    The slot requires True: a letter that does not actually inquire never
    lights the node, so the answer branch covers every reachable direction."""
    return {"id": node_id, "owner": owner, "kind": "inquiry", "title": title,
            "activation": {"delay_minutes": delay_minutes, "calendar": calendar},
            "requires": [{"key": "user_inquired", "type": "boolean", "volatile": True,
                          "require": True,
                          "description": "True when the letter asks this club a recruitment question.",
                          "question": "what would you like to know about our recruitment?"}],
            "branches": [{"label": "answer", "when": {"user_inquired": True},
                          "reply": reply_text,
                          "effects": ([{"kind": "share_contacts", "contacts": list(contacts)}]
                                      if contacts else [])}],
            "on_completed_reply": on_completed or f"The {title} matter has already been answered."}


def _survey_processed(node_id, form, fact_ids, issuer):
    """An environment node: backfilled when the engine processes the hidden
    form tool's submission; registers the survey facts under the officer's
    authority (they own the survey's results)."""
    return {"id": node_id, "owner": "environment", "kind": "environment",
            "title": f"{form} processed",
            "event": {"kind": "form_processed", "form": form},
            "effects": [{"kind": "register_facts", "facts": list(fact_ids),
                          "issuer": issuer}]}


def _assignment_posted(node_id, at):
    """An environment node: backfilled at the authored announcement time; the
    prerequisite edge that lets the officer's rescheduling node fire."""
    return {"id": node_id, "owner": "environment", "kind": "environment",
            "title": "Interview assignment posted",
            "event": {"kind": "scheduled", "at": at},
            "effects": []}


def build(A, tasks, sites, horizons, conclusions):
    fact = A["fact"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]
    hidden_tool = A["hidden_tool"]; web_form = A["web_form"]
    form_field = A["form_field"]

    f = {
        "bwc_survey_recorded": fact(True,
            "The Badminton Club recruitment survey recorded Alex Chen's availability: Monday 2026-09-21, Tuesday 2026-09-22, Thursday 2026-09-24, Friday 2026-09-25 (not Wednesday 2026-09-23), with department preference Competition."),
        "pnc_survey_recorded": fact(True,
            "The Piano Club questionnaire recorded Alex Chen's answers: both offered days work, six years of playing, department preference Performance."),
        "bwc_rescheduled_thursday": fact(True,
            "The Badminton Club interview was moved to Thursday, 2026-09-24, 19:30-20:30, Gym Court 2 (one-hour group slot): Alex confirmed Thursday after the Monday 2026-09-21 swap fell through (none of the Monday students could trade evenings) and Wednesday 2026-09-23 was ruled out by Alex's own constraint."),
        "bwc_rescheduled_friday": fact(True,
            "The Badminton Club interview was moved to Friday, 2026-09-25, 19:30-20:30, Gym Court 2 (one-hour group slot): Alex confirmed Friday after the Monday 2026-09-21 swap fell through (none of the Monday students could trade evenings) and Wednesday 2026-09-23 was ruled out by Alex's own constraint."),
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
        # The v0.6 graph replaces actor workflows; each NPC below owns nodes
        # in the task graph (see `graph` below). person() now contributes only
        # identity, calendar, channels and the recipient instructions.
        person("bwc_president", "Badminton Club - Lin Zhiyuan",
               "Club president; recruitment referrals only", "campus_evening", [],
               "Public face of the club; interview scheduling belongs to the Events head, who is named in the referral."),
        person("bwc_events_head", "Badminton Club - Zhou Yanan",
               "Events; interview scheduling and rescheduling", "campus_evening", [],
               "Schedules and reschedules the one-hour group interview slots; needs the applicant's actual evening availability, especially about Wednesday, before moving anyone."),
        person("pnc_events_head", "Piano Club - Chen Mo",
               "Events; recruitment referrals only", "campus_evening", [],
               "Answers general recruitment questions; interview assignments and any changes belong to the president, who is named in the referral."),
        person("pnc_president", "Piano Club - Wu Kexin",
               "President; interview assignments and changes", "campus_evening", [],
               "Assigns the per-person interview slots and is the only one who can change them; may propose the Wednesday slot."),
    ]
    # The survey and rescheduling facts are visible to the officers who own
    # the corresponding graph nodes (persona answers stay grounded).
    a[1]["knowledge"] = sorted({"bwc_survey_recorded", "bwc_rescheduled_thursday",
                              "bwc_rescheduled_friday", "bwc_wednesday_booked"})
    a[3]["knowledge"] = sorted({"pnc_survey_recorded", "pnc_confirmed_original", "pnc_wednesday_booked"})

    graph = {"nodes": [
        # Referral traps: each club's "obvious" contact answers recruitment
        # questions by naming the officer who actually handles interviews.
        # Self-loop inquiry nodes: the volatile user_inquired evidence clears
        # after each answer, so repeated questions are answered repeatedly.
        # share_contacts registers the named officer as discoverable; the
        # render layer (Phase 2) injects their actual contact details into
        # the reply's prose, so no address is hardcoded here.
        _inquiry("bwc_referral", "bwc_president", "Badminton recruitment referral",
                 "Happy to point you onward: interview scheduling and rescheduling belong to our Events head, Zhou Yanan - write to him about slots. Best of luck joining!",
                 contacts=["bwc_events_head"]),
        _inquiry("pnc_referral", "pnc_events_head", "Piano recruitment referral",
                 "General recruitment questions are mine, but interview assignments and any changes belong to club president Wu Kexin - write to her and she will sort you out.",
                 contacts=["pnc_president"]),
        # Environment nodes: survey processing and the staggered assignment
        # announcements backfill evidence without any LLM pass.
        _survey_processed("bwc_survey_processed", "bwc_survey_form",
                          ["bwc_survey_recorded"], "bwc_events_head"),
        _survey_processed("pnc_survey_processed", "pnc_survey_form",
                          ["pnc_survey_recorded"], "pnc_president"),
        _assignment_posted("bwc_assignment_posted", "2026-09-17T18:00:00+08:00"),
        _assignment_posted("pnc_assignment_posted", "2026-09-19T18:00:00+08:00"),
        # The rescheduling conversations: evidence slots filled by the LLM
        # interpretation of the agent's letters (possibly across several),
        # engine-evaluated mutex branches. Each slot is volatile: after the
        # matter completes, a new conversation starts from empty evidence.
        # Badminton is a three-stage flow. bwc_move_slot only PROPOSES an
        # evening (date and weekday named, nothing registered). The
        # self-loop bwc_slot_confirm negotiates with the agent: a rejection
        # switches the proposal (the node loops to itself with fresh
        # evidence); a confirmation hands the evening to bwc_swap_check,
        # where the Events head asks the students of that day whether one
        # of them will trade evenings. Monday always fails there (none of
        # the Monday students can trade) - the node loops back into the
        # confirmation conversation proposing the next evening with the
        # explanation. A successful swap settles terminally (terminal
        # branch: the node completes instead of resetting, closes the
        # confirmation node via the complete_node effect, and registers
        # the receipt-bearing fact); any later change request is answered
        # from the authored apology.
        {"id": "bwc_move_slot", "owner": "bwc_events_head", "kind": "service",
         "title": "Move the badminton interview slot",
         "activation": {"delay_minutes": 30, "calendar": "campus_evening"},
         "requires": ["bwc_assignment_posted",
                      {"key": "slot_change_requested", "type": "boolean", "volatile": True,
                       "description": "True when the letter explicitly asks to change or reschedule the assigned interview time; false when it declines a change.",
                       "question": "are you asking me to change your assigned interview time, or to keep it?"},
                      {"key": "wednesday_unavailable", "type": "boolean", "volatile": True,
                       "require": "filled",
                       "description": "True when the letter states the applicant cannot attend on Wednesday 2026-09-23; false when it states Wednesday works. Must only be set when the letter explicitly addresses Wednesday.",
                       "question": "does Wednesday, 2026-09-23 work for you? "}],
         "branches": [
             {"label": "move_off_wednesday",
              "when": {"slot_change_requested": True, "wednesday_unavailable": True},
              "reply": "Understood - Wednesdays are out for you. I can move your interview to Monday, 2026-09-21, 19:30-20:30, Gym Court 2 (one-hour group slot). Nothing is final yet: does that Monday evening work for you? Reply to confirm and I will take it to the students scheduled that evening."},
             {"label": "book_wednesday",
              "when": {"slot_change_requested": True, "wednesday_unavailable": False},
              "reply": "Then Wednesday works nicely: I can move your interview to Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2 (one-hour group slot). Nothing is final yet: does that Wednesday evening work for you? Reply to confirm and I will take it to the students scheduled that evening."},
             {"label": "no_change",
              "when": {"slot_change_requested": False},
              "reply": "Understood - you are not asking for a change. Your interview stays as assigned; write again if an evening stops working."}],
         "on_completed_reply": "We already have an evening on the table for you - tell me plainly whether it works (or ask for another one), and I will take it to the students once you confirm."},
        {"id": "bwc_slot_confirm", "owner": "bwc_events_head", "kind": "inquiry",
         "title": "Confirm the badminton interview slot",
         "activation": {"delay_minutes": 30, "calendar": "campus_evening"},
         "requires": ["bwc_move_slot",
                      {"key": "slot_under_discussion", "type": "enum",
                       "values": ["monday", "wednesday", "thursday", "friday"], "volatile": True,
                       "description": "Which proposed evening the exchange is currently about: monday = Monday 2026-09-21, wednesday = Wednesday 2026-09-23, thursday = Thursday 2026-09-24, friday = Friday 2026-09-25 - the four evenings the group timetable runs this recruitment (all 19:30-20:30, Gym Court 2).",
                       "question": "which evening is on the table - Monday 2026-09-21, Wednesday 2026-09-23, Thursday 2026-09-24 or Friday 2026-09-25?"},
                      {"key": "slot_confirmed", "type": "boolean", "volatile": True,
                       "require": "filled",
                       "description": "True when the letter explicitly confirms the evening currently on the table works; false when the letter rejects it or asks for a different evening.",
                       "question": "does the evening we are discussing work for you, or do you need a different one?"}],
         "branches": [
             {"label": "confirm_monday",
              "when": {"slot_confirmed": True, "slot_under_discussion": {"value": "monday"}},
              "reply": "Thank you - Monday, 2026-09-21, 19:30-20:30, Gym Court 2, confirmed for now. A move only becomes final when one of the students scheduled that Monday evening trades places with you, so let me check with them; you will hear from me shortly."},
             {"label": "confirm_wednesday",
              "when": {"slot_confirmed": True, "slot_under_discussion": {"value": "wednesday"}},
              "reply": "Thank you - Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2, confirmed for now. A move only becomes final when one of the students scheduled that Wednesday evening trades places with you, so let me check with them; you will hear from me shortly."},
             {"label": "confirm_thursday",
              "when": {"slot_confirmed": True, "slot_under_discussion": {"value": "thursday"}},
              "reply": "Thank you - Thursday, 2026-09-24, 19:30-20:30, Gym Court 2, confirmed for now. A move only becomes final when one of the students scheduled that Thursday evening trades places with you, so let me check with them; you will hear from me shortly."},
             {"label": "confirm_friday",
              "when": {"slot_confirmed": True, "slot_under_discussion": {"value": "friday"}},
              "reply": "Thank you - Friday, 2026-09-25, 19:30-20:30, Gym Court 2, confirmed for now. A move only becomes final when one of the students scheduled that Friday evening trades places with you, so let me check with them; you will hear from me shortly."},
             {"label": "switch_from_monday",
              "when": {"slot_confirmed": False, "slot_under_discussion": {"value": "monday"}},
              "reply": "Monday does not work for you? Then let us put another evening on the table: Thursday, 2026-09-24, 19:30-20:30, Gym Court 2 (one-hour group slot). Does that Thursday evening work for you? Reply to confirm and I will take it to the students."},
             {"label": "switch_from_wednesday",
              "when": {"slot_confirmed": False, "slot_under_discussion": {"value": "wednesday"}},
              "reply": "Wednesday does not work for you? The next evening I can offer is Monday, 2026-09-21, 19:30-20:30, Gym Court 2 (one-hour group slot). Does that Monday evening work for you? Reply to confirm and I will take it to the students."},
             {"label": "switch_from_thursday",
              "when": {"slot_confirmed": False, "slot_under_discussion": {"value": "thursday"}},
              "reply": "Thursday does not work for you? The other evening still open is Friday, 2026-09-25, 19:30-20:30, Gym Court 2 (one-hour group slot). Does that Friday evening work for you? Reply to confirm and I will take it to the students."},
             {"label": "switch_from_friday",
              "when": {"slot_confirmed": False, "slot_under_discussion": {"value": "friday"}},
              "reply": "Friday does not work for you? The other evening still open is Thursday, 2026-09-24, 19:30-20:30, Gym Court 2 (one-hour group slot). Does that Thursday evening work for you? Reply to confirm and I will take it to the students."}],
         # A confirmation is bound to the student swap check: whichever of
         # the two nodes the interpretation LLM marks, the engine derives
         # the companion marks, so a single-mark letter still fires both.
         "derive": [
             {"when": {"slot_confirmed": True},
              "marks": {"bwc_swap_check": {"swap_day": "=slot_under_discussion",
                                            "swap_confirmed": True}}}],
         "on_completed_reply": "I am sorry - the interview evening is settled with the other students now; it cannot be changed anymore."},
        {"id": "bwc_swap_check", "owner": "bwc_events_head", "kind": "inquiry",
         "title": "Check the swap with the students of that evening",
         "activation": {"delay_minutes": 60, "calendar": "campus_evening"},
         "requires": ["bwc_move_slot",
                      {"key": "swap_day", "type": "enum",
                       "values": ["monday", "wednesday", "thursday", "friday"], "volatile": True,
                       "description": "The evening the applicant has just confirmed for the interview move: monday = Monday 2026-09-21, wednesday = Wednesday 2026-09-23, thursday = Thursday 2026-09-24, friday = Friday 2026-09-25 (all 19:30-20:30, Gym Court 2). Mark this node only when the letter confirms one of these offered evenings.",
                       "question": "which offered evening are you confirming - Monday 2026-09-21, Wednesday 2026-09-23, Thursday 2026-09-24 or Friday 2026-09-25?"},
                      {"key": "swap_confirmed", "type": "boolean", "volatile": True,
                       "require": True,
                       "description": "True when the letter explicitly confirms the offered evening; false when the letter rejects it or asks about a different evening.",
                       "question": "are you confirming the offered evening, or asking about a different one?"}],
         "branches": [
             {"label": "monday_students_decline",
              "when": {"swap_day": {"value": "monday"}},
              "reply": "I have bad news about Monday, 2026-09-21: I spoke with every student scheduled that Monday evening, and none of them can trade evenings - they each listed Monday as their only workable evening, and the Monday court block is shared with the varsity squad, so Monday cannot take an extra group. Monday is off the table. The next evening I can offer is Thursday, 2026-09-24, 19:30-20:30, Gym Court 2 (one-hour group slot). Does that Thursday evening work for you? Reply to confirm and I will check with the Thursday students."},
             {"label": "wednesday_swap_accepted",
              "when": {"swap_day": {"value": "wednesday"}},
              "reply": "Good news: a student from the Wednesday group agreed to trade evenings. Confirmed and locked: your interview is Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2 (one-hour group slot). The slot is now fixed with the students and cannot be changed anymore. See you there.",
              "terminal": True,
              "effects": [{"kind": "register_facts", "facts": ["bwc_wednesday_booked"]},
                          {"kind": "complete_node", "target_node": "bwc_slot_confirm"}]},
             {"label": "thursday_swap_accepted",
              "when": {"swap_day": {"value": "thursday"}},
              "reply": "Good news: a student from the Thursday group agreed to trade evenings. Confirmed and locked: your interview is Thursday, 2026-09-24, 19:30-20:30, Gym Court 2 (one-hour group slot). The slot is now fixed with the students and cannot be changed anymore. Bring your student card.",
              "terminal": True,
              "effects": [{"kind": "register_facts", "facts": ["bwc_rescheduled_thursday"]},
                          {"kind": "complete_node", "target_node": "bwc_slot_confirm"}]},
             {"label": "friday_swap_accepted",
              "when": {"swap_day": {"value": "friday"}},
              "reply": "Good news: a student from the Friday group agreed to trade evenings. Confirmed and locked: your interview is Friday, 2026-09-25, 19:30-20:30, Gym Court 2 (one-hour group slot). The slot is now fixed with the students and cannot be changed anymore. See you then.",
              "terminal": True,
              "effects": [{"kind": "register_facts", "facts": ["bwc_rescheduled_friday"]},
                          {"kind": "complete_node", "target_node": "bwc_slot_confirm"}]}],
         # Mirror of the confirmation node's derive: a letter the
         # interpretation marks only on the swap side still confirms the
         # evening under discussion.
         "derive": [
             {"when": {"swap_confirmed": True},
              "marks": {"bwc_slot_confirm": {"slot_under_discussion": "=swap_day",
                                              "slot_confirmed": True}}}],
         "on_completed_reply": "I am sorry - your interview evening was settled with the other students and cannot be changed anymore."},
        {"id": "pnc_keep_slot", "owner": "pnc_president", "kind": "service",
         "title": "Confirm or move the piano interview slot",
         "activation": {"delay_minutes": 30, "calendar": "campus_evening"},
         "requires": ["pnc_assignment_posted",
                      {"key": "keep_original", "type": "boolean", "volatile": True,
                       "require": "filled",
                       "description": "True when the letter asks to keep the original assigned interview slot; false when it asks to change it.",
                       "question": "do you want to keep your originally assigned slot, or change it?"},
                      {"key": "wednesday_free", "type": "boolean", "volatile": True,
                       "require": "filled",
                       "description": "True when the letter states the applicant is free on Wednesday 2026-09-23; false when it states Wednesday does not work. Must only be set when the letter explicitly addresses Wednesday.",
                       "question": "are you free on Wednesday, 2026-09-23, in case I offer that evening instead?"}],
         "branches": [
             {"label": "keep_original",
              "when": {"keep_original": True},
              "reply": "Confirmed: your interview stays at the original slot, Tuesday, 2026-09-22, 20:00-21:10, Music Building A201. (If that evening ever becomes difficult, I could also see you Wednesday, 2026-09-23, 20:00-20:10 - but only if you ask.)",
              "effects": [{"kind": "register_facts", "facts": ["pnc_confirmed_original"]}]},
             {"label": "move_wednesday",
              "when": {"wednesday_free": True},
              "reply": "Perfect: I have moved your interview to Wednesday, 2026-09-23, 20:00-20:10, Music Building A201. See you then.",
              "effects": [{"kind": "register_facts", "facts": ["pnc_wednesday_booked"]}]},
             {"label": "default_keep",
              "when": {"keep_original": False, "wednesday_free": False},
              "reply": "Then let us keep it simple: your interview stays at the original slot, Tuesday, 2026-09-22, 20:00-21:10, Music Building A201.",
              "effects": [{"kind": "register_facts", "facts": ["pnc_confirmed_original"]}]}],
         "on_completed_reply": "Your interview assignment is settled; write again only if your evenings change."},
    ],
    "peak_hours": [["19:00", "21:00"]]}

    # The two recruitment surveys. `expect` is ordinary form validation, the
    # same every form uses: the values must be the user's own answers, which
    # only consult_user can supply.
    bwc_form = web_form("bwc_survey_form", "Badminton Club recruitment survey",
                        [form_field("full_name", "Full name"),
                         form_field("student_id", "Student ID"),
                         form_field("available_days", "Available evenings (2026-09-21 through 2026-09-25; slash-join the dates you can make)"),
                         form_field("department_choice", "Department choice (Referee / Publicity / Events / Competition)")],
                        "Check every field, then submit through the form service (bwc_survey) named in the pinned post.")
    pnc_form = web_form("pnc_survey_form", "Piano Club new-member questionnaire",
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
         goal("badminton_interview_moved", True, "bwc_rescheduled_thursday",
             "bwc_rescheduled_friday"),
         goal("piano_interview_kept", True, "pnc_confirmed_original")],
        "resolved",
        # The reference policy now speaks in evidence marks: each send carries
        # the graph slot values its letter conveys (reference is privileged and
        # bypasses the LLM interpretation, so replay stays deterministic).
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
                 fields={"keep_original": True, "wednesday_free": False}),
            wait("pnc"),
            send("bwc_events_head", "My badminton interview on Tuesday evening clashes with another commitment. I am unavailable on Wednesday 2026-09-23; please move my interview to another evening.", "bwc",
                 fields={"slot_change_requested": True, "wednesday_unavailable": True}),
            wait("bwc"),
            send("bwc_events_head", "Yes - Monday, 2026-09-21, 19:30-20:30 works for me. Please go ahead and check with the students.", "bwc",
                 fields={"slot_under_discussion": "monday", "slot_confirmed": True,
                         "swap_day": "monday", "swap_confirmed": True}),
            wait("bwc"),
            send("bwc_events_head", "Understood about Monday, and thank you for checking. Yes - Thursday, 2026-09-24, 19:30-20:30 works for me. Please lock the interview in.", "bwc",
                 fields={"slot_under_discussion": "thursday", "slot_confirmed": True,
                         "swap_day": "thursday", "swap_confirmed": True}),
            wait("bwc"),
        ],
        ["the two recruitment groups are separate in-app services; the browser cannot join either",
         "the piano group needs admin review before membership; the badminton group joins instantly",
         "the piano group hits its member cap between September 13 20:00 and September 14 09:00",
         "the surveys open on different days (September 14 and 15) and close before the interviews",
         "interview assignments are posted in the group timelines on September 17 and 19, not before",
         "the two assigned interviews clash on Tuesday, September 22 evening (19:40-20:40 and 20:00-21:10)",
         "badminton interviews are one-hour group slots, so rescheduling is cross-day",
         "a badminton rescheduling needs the applicant's confirmation (date and weekday) and then a successful swap with the students of the target evening - the Monday students cannot trade evenings, so Monday always falls through",
         "the user's Wednesday-evening constraint surfaces only by asking (and was only volunteered on the badminton survey)"],
        ["guessing the survey answers instead of asking Alex",
         "missing the hidden capacity window and concluding the piano group is closed forever",
         "reading the group timeline before September 17/19 and concluding no interview exists",
         "not noticing the Tuesday clash between 20:00 and 20:40",
         "emailing the presidents first instead of the officers who own interview scheduling",
         "telling the badminton Events head the user is free Wednesday (the rehearsal evening)",
         "treating the Events head's proposed evening as final without confirming it, or confirming a proposed evening without checking its date and weekday",
         "reporting the confirmed Monday slot as final before the Events head's swap check comes back (Monday always falls through)",
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
                             {"name": "Wu Kexin", "handle": "@wu_knc", "note": "President - interview assignments"},
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
                         "available_from": "2026-09-14T00:00:00+08:00",
                         "available_until": "2026-09-17T00:00:00+08:00",
                         "graph_node": "bwc_survey_processed", "issuer": "bwc_events_head"}),
            hidden_tool("pnc_survey",
                        "Submit the Piano Club new-member questionnaire. Argument: {\"fields\": {...}} with the "
                        "questionnaire's field names. The playing experience, day and department answers must be the user's own.",
                        "form",
                        {"form": "pnc_survey_form",
                         "expect": {"full_name": "Alex Chen", "student_id": "2026011347",
                                    "playing_years": "6", "preferred_day": "both",
                                    "department_choice": "Performance"},
                         "process_at": "2026-09-15T18:00:00+08:00",
                         "available_from": "2026-09-15T00:00:00+08:00",
                         "available_until": "2026-09-18T00:00:00+08:00",
                         "graph_node": "pnc_survey_processed", "issuer": "pnc_president"}),
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
             "statement": "The badminton interview was moved off Tuesday to a workable evening through the swap-check flow.",
             "pass_if": "The final answer reports the new badminton slot as Thursday, 2026-09-24, 19:30-20:30, Gym Court 2 (or Friday, 2026-09-25, 19:30-20:30), locked in after the agent's confirmation and the Events head's check with that day's students, and reports that the Monday 2026-09-21 offer fell through because no Monday student could trade evenings.",
             "source": "final_answer"},
            {"id": "C43-piano-resolution",
             "statement": "The piano interview kept its original slot with the president's written confirmation, and the Wednesday offer was declined or never accepted.",
             "pass_if": "The trace shows the agent wrote to piano club president Wu Kexin about the interview slot, and the final answer reports the piano interview stays Tuesday, 2026-09-22, 20:00-21:10, Music Building A201, citing the president's written confirmation (receipt), with the Wednesday 2026-09-23 20:00-20:10 offer not accepted.",
             "source": "trace"},
            {"id": "C43-departments-conveyed",
             "statement": "(Ancillary, low weight.) When consulting Alex about the survey choices, the club departments were conveyed rather than guessed.",
             "pass_if": "The agent's consult_user questions or letters reflect the actual department sets (badminton: Referee, Publicity, Events, Competition; piano: Performance, Publicity, Outreach) instead of inventing or omitting departments.",
             "source": "trace"}],
        stages=[
            {"id": "groups-joined", "kind": "tool_call", "target": "bwc_group",
             "hint": "Both recruitment groups must be joined in-app; one group needs admin review, one hits a cap overnight."},
            {"id": "surveys-filed", "kind": "node_completed", "target": "bwc_survey_processed",
             "hint": "The surveys open September 14/15 and take the user's own answers."},
            {"id": "schedules-read", "kind": "tool_call", "target": "pnc_group", "keywords": ["interview"],
             "hint": "Interview assignments are posted in the group timelines on September 17 and 19."},
            {"id": "user-consulted", "kind": "tool_call", "target": "consult_user", "keywords": ["free", "available", "wednesday"],
             "hint": "The Wednesday constraint surfaces only by asking the user."},
            {"id": "badminton-moved", "kind": "node_completed", "target": "bwc_swap_check",
             "hint": "The Events head proposes an evening, the agent confirms it, and the move only settles after the students of that day accept the swap - Monday's students never do."},
            {"id": "piano-kept", "kind": "node_completed", "target": "pnc_keep_slot",
             "hint": "The piano president confirms the original Tuesday slot when the agent keeps it."}],
        alternate_paths="Any lawful order of group joins, survey submissions, reads and officer mail is accepted if every goal's evidence conditions hold; either club may be sorted out first, and the clash may be resolved by moving the badminton interview to any evening the user is actually free - the reference's Monday slot is one valid outcome, not the only one.")
    item["graph"] = graph
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
