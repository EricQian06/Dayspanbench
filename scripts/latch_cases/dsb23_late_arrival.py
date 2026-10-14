"""DSB-23 <- LATCH case cross-pets-travel-late-arrival-001 (Lyon pet stay).
A delayed late-evening train arrival invalidated by a written hotel pet
acceptance, an explicit late-check-in extension and a companion's
supervision acknowledgement rebound to the current itinerary."""

LATCH_CASE = "cross-pets-travel-late-arrival-001"


def build(A, tasks, sites, horizons, conclusions):
    # ---- DSB-23 <- LATCH cross-pets-travel-late-arrival-001 -----------------
    # A pet-inclusive hotel booking under a moving arrival time. The LATCH
    # pet_trip.records becomes a hidden kind="catalog" tool (trip_records,
    # discoverable via web_search keywords) carrying the six Lyon hotel
    # listings plus the rail arrival record - the 15 kg dog-limit, 22:00
    # late-desk, 1.9 m garage, afternoon-only and 500 EUR listings are the
    # decoys. The XPT-PET event (hotel's written pet acceptance published at
    # 19:00 after the verification request) becomes a catalog update swapping
    # villa-v1 for villa-verified; the XPT-DELAY event (train slips to 23:40
    # at 20:30) becomes a catalog update swapping train-v1 for train-v2 plus
    # a page_update at the same virtual time; the written late-check-in
    # extension late-XPT2 becomes a further catalog update the following
    # morning swapping villa-verified for villa-extended (late check-in until
    # 00:30). The LATCH stay.book becomes a hidden kind="select" tool
    # (stay_book) linked to the catalog: only the villa-extended row is
    # acceptable, so booking on the stale 23:50 limit or an ineligible hotel
    # is rejected. The LATCH user.dialogue becomes a hidden kind="dialogue"
    # tool (camille_dialogue): the sparse prompt's pet/logistics/authorization
    # facts never appear on any page, only by asking. The hotel desk keeps the
    # DSB mail surface for the written pet/parking acceptance, and the
    # companion Lea acknowledges supervision by mail - her acknowledgement is
    # bound to the current (delayed) itinerary and only exists after the delay
    # is known. The case deadline (Apr 16 22:30 Paris) is 4.5h after start;
    # DSB validation requires a >= 2-day horizon, so the deadline moves to
    # Apr 18 08:00 Paris time - the morning after the first covered night -
    # with the booking gates unchanged at the case's own event times.
    fact = A["fact"]; lookup = A["lookup"]; document = A["document"]
    acknowledge = A["acknowledge"]; reply = A["reply"]
    workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; hidden_tool = A["hidden_tool"]
    page_update = A["page_update"]

    f = {
        "pet_accepted": fact(True,
                              "Written hotel permission pet-accept-XPT: the Villa des Roses accepts Nino (pet-XPT, 28 kg, current vet letter) for 2027-04-16 and 2027-04-17; the dog may not be left unattended, and open-air parking fits the 2.05 m car."),
        "train_arrival": fact("23:40",
                              "Train train-XPT is delayed: the current arrival (version 2) is 23:40 on 2027-04-16; with the 25-minute station-to-hotel transfer, check-in would land at 00:05 on 2027-04-17."),
        "late_extension": fact("00:30",
                               "Written hotel confirmation late-XPT2 extends late check-in at the Villa des Roses until 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits.",
                               available_at="2027-04-17T08:30:00+02:00"),
        "companion_ack": fact(True,
                              "Lea Bernard explicitly acknowledged staying with Nino during parking, check-in and the whole stay on the current delayed itinerary (arrival 23:40), with no unattended periods.",
                              available_at="2027-04-16T20:30:00+02:00"),
        "stay_confirmed": fact(True,
                               "Reservation stay-XPT1 confirms two nights at the Villa des Roses, 2027-04-16 to 2027-04-18, for Camille Moreau and Nino: written 28 kg pet acceptance, the extended 00:30 late check-in, open-air parking for the 2.05 m car and Lea's supervision linked; total 378 EUR; no payment taken."),
        "total_cost": fact(378,
                           "The stay total is 378 EUR - 310 EUR room for two nights, 20 EUR pet fee and 48 EUR open-air parking for two nights - within the 420 EUR budget."),
    }
    a = [
        person("hotel_desk", "Villa des Roses hotel desk·Marc Aubert",
               "written pet acceptance, parking terms and late check-in extensions", "paris_daily",
               [workflow("Pet and parking verification",
                         ["pet", "dog", "nino", "28", "weight", "parking", "verify", "acceptance",
                          "vet", "letter"],
                         [],
                         [acknowledge(business(10)),
                          lookup(["pet_accepted"], business(40),
                                 "check the written pet acceptance and parking terms"),
                          document(["pet_accepted"], business(10)),
                          reply()]),
                 workflow("Late check-in extension",
                          ["extension", "extend", "midnight", "00:05", "past the", "later than"],
                          [],
                          [acknowledge(business(10)),
                           lookup(["late_extension"], business(40),
                                  "issue the written late check-in extension for the delayed itinerary"),
                           document(["late_extension"], business(10)),
                           reply()], id="extension")],
               "Issues written pet acceptances naming the exact dog, weight and vet letter, parking terms and late-check-in extensions for the current itinerary; generic pets-welcome marketing never substitutes for the written permission."),
        person("companion_lea", "Travel companion·Lea Bernard",
               "animal supervision during the trip", "paris_daily",
               [workflow("Supervision acknowledgement",
                         ["lea", "companion", "supervise", "supervision", "nino", "dog", "stay",
                          "handoff", "cover", "watch"],
                         [],
                         [acknowledge(business(10)),
                          lookup(["companion_ack"], business(30),
                                 "confirm her supervision acknowledgement for the current itinerary"),
                          document(["companion_ack"], business(10)),
                          reply()])],
               "May stay with Nino and acknowledges supervision only for the itinerary shown to her; an acknowledgement for an older arrival time does not carry over after a delay."),
        person("rail_desk", "Rail service desk·Julien Fabre",
               "current train arrival and delay status", "paris_daily",
               [workflow("Train arrival status",
                         ["train", "rail", "arrival", "delay", "delayed", "station", "transfer",
                          "schedule"],
                         [],
                         [acknowledge(business(10)),
                          lookup(["train_arrival"], business(30),
                                 "check the current arrival time of train train-XPT"),
                          document(["train_arrival"], business(10)),
                          reply()])],
               "Reports only the current published arrival; a delayed arrival invalidates plans whose transfer ends after the hotel's written check-in limit."),
    ]
    # The hotel desk attests the stay confirmation through the hidden booking
    # service, and the rail desk attests the delayed arrival through the
    # live rail record; neither issues those through a mail workflow.
    a[0]["knowledge"] = sorted(set(a[0]["knowledge"]) | {"stay_confirmed", "total_cost"})
    a[2]["knowledge"] = sorted(set(a[2]["knowledge"]) | {"train_arrival"})
    entries = [
        {"id": "villa-v1", "title": "Villa des Roses - two nights, pets considered (awaiting verification)",
         "text": "Two nights April 16-18; room 310 EUR, pet fee 20 EUR, open-air parking 24 EUR per night, total 378 EUR; late check-in until 23:50; dog acceptance pending written verification. Parking height unrestricted (open air).",
         "fields": {"hotel": "Villa des Roses", "nights": 2, "room_eur": 310, "pet_eur": 20,
                    "parking_eur_per_night": 24, "total_eur": 378, "late_until": "2027-04-16T23:50:00+02:00",
                    "version": 1, "status": "awaiting_verification"},
         "expires_at": "2027-04-16T19:00:00+02:00"},
        {"id": "small-pets", "title": "Small-Pets Hotel - 15 kg dog limit",
         "text": "Cheapest listing at 300 EUR, but only accepts dogs up to 15 kg; Nino weighs 28 kg.",
         "fields": {"hotel": "Small-Pets Hotel", "dog_limit_kg": 15, "total_eur": 300, "status": "available"}},
        {"id": "early-desk", "title": "Early-Desk Inn - late check-in only until 22:00",
         "text": "Accepts dogs up to 35 kg, 350 EUR, but the desk closes at 22:00 - before even the original 23:10 arrival.",
         "fields": {"hotel": "Early-Desk Inn", "dog_limit_kg": 35,
                    "late_until": "2027-04-16T22:00:00+02:00", "total_eur": 350, "status": "available"}},
        {"id": "low-garage", "title": "Low-Garage Hotel - 1.9 m covered garage",
         "text": "Accepts dogs up to 35 kg, 360 EUR, but its covered garage is limited to 1.9 m; the car is 2.05 m tall.",
         "fields": {"hotel": "Low-Garage Hotel", "dog_limit_kg": 35, "parking_height_m": 1.9,
                    "total_eur": 360, "status": "available"}},
        {"id": "afternoon-only", "title": "Afternoon-Only Guesthouse - check-in until 15:00",
         "text": "280 EUR, but check-in is possible only until 15:00; useless for a late-evening arrival.",
         "fields": {"hotel": "Afternoon-Only Guesthouse", "checkin_only": "15:00",
                    "total_eur": 280, "status": "available"}},
        {"id": "premium", "title": "Premium Palace - 500 EUR",
         "text": "Accepts dogs up to 35 kg with late check-in, but at 500 EUR it exceeds the 420 EUR budget.",
         "fields": {"hotel": "Premium Palace", "dog_limit_kg": 35, "total_eur": 500, "status": "available"}},
        {"id": "train-v1", "title": "train-XPT - arrival 23:10 (version 1)",
         "text": "Current rail record: train-XPT arrives 2027-04-16 at 23:10; station-to-hotel transfer takes 25 minutes.",
         "fields": {"kind": "train", "train": "train-XPT", "version": 1,
                    "arrival": "2027-04-16T23:10:00+02:00"},
         "expires_at": "2027-04-16T20:30:00+02:00"},
    ]
    villa_verified = {"id": "villa-verified", "title": "Villa des Roses - written 28 kg pet acceptance (late check-in until 23:50)",
                      "text": "Written permission pet-accept-XPT: Nino (pet-XPT, 28 kg, current vet letter) accepted for 2027-04-16 and 2027-04-17; no unattended periods; open-air parking fits the 2.05 m car. Room 310 EUR, pet fee 20 EUR, parking 48 EUR, total 378 EUR. Late check-in until 23:50 - the transfer must end by then.",
                      "fields": {"hotel": "Villa des Roses", "nights": 2, "total_eur": 378,
                                 "late_until": "2027-04-16T23:50:00+02:00", "version": 1,
                                 "pet_accepted": True, "parking": "open_air", "car_height_m": 2.05,
                                 "status": "available"},
                      "expires_at": "2027-04-17T08:30:00+02:00"}
    train_v2 = {"id": "train-v2", "title": "train-XPT - DELAYED, arrival 23:40 (version 2)",
                "text": "Updated rail record: train-XPT now arrives 2027-04-16 at 23:40; with the 25-minute transfer, check-in lands at 00:05 on 2027-04-17 - past the hotel's 23:50 limit unless a written extension is obtained.",
                "fields": {"kind": "train", "train": "train-XPT", "version": 2,
                           "arrival": "2027-04-16T23:40:00+02:00", "delayed": True},
                "facts": ["train_arrival"], "issuer": "rail_desk"}
    villa_extended = {"id": "villa-extended", "title": "Villa des Roses - written extension, late check-in until 00:30",
                      "text": "Written confirmation late-XPT2: late check-in extended to 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits. Written pet acceptance pet-accept-XPT, open-air parking and the 378 EUR total unchanged. This is a live listing, not a confirmed booking.",
                      "fields": {"hotel": "Villa des Roses", "nights": 2, "total_eur": 378,
                                 "late_until": "2027-04-17T00:30:00+02:00", "version": 2,
                                 "pet_accepted": True, "parking": "open_air", "car_height_m": 2.05,
                                 "extension": "late-XPT2", "status": "available"},
                      "facts": ["late_extension"], "issuer": "hotel_desk"}
    tasks.append(task(
        "DSB-23", "Lyon pet stay: delayed late arrival, written pet acceptance and supervision", "pets_animals",
        "2027-04-16T18:00:00+02:00", "2027-04-18T18:00:00+02:00",
        "Book two nights in Lyon for April 16-18 for me and my dog Nino, within 420 EUR including pet fees and parking; my train arrives 23:10 on Friday and I return Sunday at 10:38. Ask me for the missing constraints and authorization first; the hotel must accept this exact dog in writing, someone must stay with him the whole time, and watch the arrival time - if the train slips, re-check before booking. No payment, no pet-policy workaround.",
        {"city": "Lyon", "checkin": "2027-04-16", "checkout": "2027-04-18", "budget_eur": 420}, [],
        [page("lyon-intro", "Lyon pet travel board",
              "Synthetic hotel and rail listings for a Lyon stay with a dog; listing claims alone do not establish pet acceptance. Current hotel terms and the rail arrival record are found through the trip records service (trip_records), and both can change - the train may slip and the hotel's terms with it, so re-check before booking. Personal constraints and authorization can be clarified through the traveler desk (camille_dialogue). Written pet and parking acceptance comes from the hotel desk by mail; supervision is acknowledged by the companion herself by mail.",
              [], "Lyon hotel listings, the rail arrival record and the traveler requirements desk."),
         page("lyon-contacts", "Hotel, companion and rail contacts",
              "The Villa des Roses hotel desk (Marc Aubert) issues written pet acceptances and late-check-in extensions; travel companion Lea Bernard acknowledges animal supervision; the rail service desk (Julien Fabre) reports the current train arrival. All answer daily during business hours.",
              ["hotel_desk", "companion_lea", "rail_desk"], "Contacts for the hotel desk, the travel companion and the rail service desk."),
         page("lyon-entry", "Pet stay booking service",
              "Stays are booked through the booking service (stay_book): pick one current trip_records listing whose written terms accept the exact dog and parking and whose late-check-in limit covers the current arrival plus the 25-minute transfer; obtain the companion's supervision acknowledgement for that same itinerary and the traveler's approval of the exact plan (hotel, pet policy, current arrival deadline, supervision, total); then request that one stay. At most one booking; the dog is never left unattended and the driver or desk is never a supervision substitute; no payment.",
              [], "Pet stay booking service: written exact-dog acceptance, current arrival fit, named supervision, one booking, no payment.")],
        f, a,
        [goal("pet_acceptance_written", True, "pet_accepted"),
         goal("train_arrival_current", "23:40", "train_arrival"),
         goal("late_checkin_deadline", "00:30", "late_extension"),
         goal("companion_supervision_acknowledged", True, "companion_ack"),
         goal("stay_confirmed", True, "stay_confirmed"),
         goal("total_cost", 378, "total_cost")],
        "stay_booked",
        [{"op": "visit_page", "page": "lyon-contacts"},
         {"op": "discover", "name": "camille_dialogue"},
         {"op": "tool", "name": "camille_dialogue", "args": {"question": "What are Nino's details, your travel logistics and your approval conditions for the hotel booking?"}},
         {"op": "discover", "name": "trip_records"},
         {"op": "tool", "name": "trip_records", "args": {"query": "Lyon"}},
         send("hotel_desk", "Please issue the written pet acceptance for Nino (28 kg, current vet letter), the parking terms and the late check-in limit for April 16-18", "pet"),
         {"op": "advance", "at": "2027-04-16T20:35:00+02:00"},
         {"op": "tool", "name": "trip_records", "args": {"query": "train"}},
         wait("pet"),
         send("companion_lea", "The train is now delayed to 23:40 with check-in around 00:05; please confirm you will stay with Nino during parking, check-in and the whole stay on this itinerary", "lea"),
         wait("lea"),
         {"op": "tool", "name": "trip_records", "args": {"query": "villa"}},
         send("hotel_desk", "The delayed 23:40 arrival plus the 25-minute transfer lands at 00:05, past the 23:50 limit; please issue a written late check-in extension for this itinerary", "extension"),
         wait("extension"),
         {"op": "tool", "name": "camille_dialogue", "args": {"question": "Do you approve the exact plan: Villa des Roses two nights, written 28 kg pet acceptance, extension to 00:30, Lea supervising Nino throughout, total 378 EUR?"}},
         {"op": "discover", "name": "stay_book"},
         {"op": "tool", "name": "stay_book", "args": {"entry": "villa-extended"}},
         {"op": "advance", "at": "2027-04-17T15:00:00+02:00"},
         {"op": "tool", "name": "stay_book", "args": {"query": "stay"}}],
        ["evening train delay rewrites the arrival record and breaks the 23:50 check-in fit",
         "written hotel extension lands the next morning and gates the booking",
         "companion acknowledgement exists only for the current delayed itinerary",
         "search-discoverable listings with five ineligible hotels",
         "hidden booking service revalidates the live listing at booking time",
         "sparse prompt: pet, logistics and authorization facts only surface through dialogue"],
        ["booking against the withdrawn 23:50 limit after the delay",
         "choosing an ineligible hotel (15 kg limit, 22:00 desk, 1.9 m garage, 15:00 check-in, 500 EUR)",
         "reusing a supervision acknowledgement made for the old 23:10 itinerary",
         "accepting pets-welcome marketing instead of the written exact-dog acceptance",
         "leaving Nino unattended during parking or check-in",
         "booking before the traveler approves the exact plan after the delay"],
        extra_tools=("check_schedule",),
        hidden_tools=(
            hidden_tool("trip_records",
                        "Lyon pet-trip records. Argument: query (optional string), e.g. \"Lyon\", \"villa\", \"train\" or \"pet\". Returns the current hotel terms (pet limits, parking, late check-in, totals) and the current rail arrival record; rows can change or disappear as the train slips and the hotel reissues terms, so re-check before booking.",
                        "catalog",
                        {"keywords": ["hotel", "lyon", "pet", "dog", "stay", "train", "arrival",
                                      "trip", "travel", "parking", "late"],
                         "clue": "A trip records service named trip_records lists the current Lyon pet-friendly hotel terms and the rail arrival record.",
                         "entries": entries,
                         "updates": [{"at": "2027-04-16T19:00:00+02:00",
                                      "remove": ["villa-v1"], "add": [villa_verified]},
                                     {"at": "2027-04-16T20:30:00+02:00",
                                      "remove": ["train-v1"], "add": [train_v2]},
                                     {"at": "2027-04-17T08:30:00+02:00",
                                      "remove": ["villa-verified"], "add": [villa_extended]}]}),
            hidden_tool("stay_book",
                        "Pet stay booking service. Argument: {\"entry\": listing_id} to request the stay shown in one current trip_records row, or {\"query\": text} to read back the current booking status. Book only the plan the traveler has approved: written exact-dog acceptance, a late-check-in limit that covers the current arrival plus the 25-minute transfer, a companion supervision acknowledgement for that same itinerary, and the total within budget. At most one booking; the dog is never left unattended; no payment is taken.",
                        "select",
                        {"catalog": "trip_records", "expect_entry": "villa-extended",
                         "expect": {"total_eur": 378, "pet_accepted": True},
                         "process_at": "2027-04-17T09:30:00+02:00", "calendar": "paris_daily",
                         "result_text": "Stay confirmed: reservation stay-XPT1, Villa des Roses, two nights 2027-04-16 to 2027-04-18, for Camille Moreau and Nino - written 28 kg pet acceptance (pet-accept-XPT), late check-in extended to 00:30 (late-XPT2) for the delayed 23:40 arrival, open-air parking for the 2.05 m car, Lea Bernard's supervision linked; total 378 EUR; no payment taken. Arrival and the stay itself remain in the future.",
                         "reject_text": "The booking was returned: the listing is stale or does not match an approvable plan - the written pet acceptance, the current arrival fit, the companion acknowledgement and the traveler's approval must all hold; nothing was booked.",
                         "facts": ["stay_confirmed", "total_cost"], "issuer": "hotel_desk",
                         "page_update": {"page": "lyon-entry",
                                         "snippet": "Booking service: an approved stay request is being processed; check the service status for the outcome."}}),
            hidden_tool("camille_dialogue",
                        "Ask the traveler, Camille Moreau, one question. Argument: {\"question\": text}. She answers only what is explicitly asked and does not volunteer other facts.",
                        "dialogue",
                        {"persona": "Camille Moreau (traveler with dog Nino), fond of her dog and exact about logistics: she answers only what is asked, insists on written acceptance and current arrival times, and approves one plan at a time.",
                         "dialogue_mode": "llm",
                         "rules": [
                             {"keywords": ["pet", "dog", "nino", "weight", "chip", "vet", "letter",
                                           "accept", "alone", "unattended"],
                              "answer": "Nino weighs 28 kg, has existing chip pet-XPT and a current vet letter. The hotel must accept this exact dog in writing, and he must never be left alone - not even during parking or check-in."},
                             {"keywords": ["logistics", "car", "parking", "height", "transfer",
                                           "station", "minutes", "checkout", "return", "train", "arrival"],
                              "answer": "The car is 2.05 m tall and needs confirmed parking. The station-to-hotel transfer takes 25 minutes; my return train leaves Sunday at 10:38 after a 09:00 checkout. Re-check the current arrival time before booking - if the train slips, the old plan no longer fits."},
                             {"keywords": ["companion", "lea", "supervision", "supervise", "who",
                                           "watch", "cover"],
                              "answer": "My companion Lea may stay with Nino and must explicitly confirm it herself - for the itinerary as it actually stands, not an outdated one."},
                             {"keywords": ["approve", "approval", "permission", "confirm", "plan",
                                           "book"],
                              "answer": "Show me the exact hotel, its pet policy, the current arrival deadline, the supervision arrangement and the full total, and I will approve that one plan. If the arrival time or the supervision changes, ask me again. No payment and no pet-policy workaround."},
                             {"keywords": ["request", "budget", "cost", "total", "eur", "nights",
                                           "book", "lyon"],
                              "answer": "Book two nights in Lyon for April 16-18 for me and Nino, total within 420 EUR including pet fees and parking."},
                         ],
                         "default": "Please ask me about Nino, the travel logistics, supervision, budget or approval."}),
        ),
        page_updates=[page_update("lyon-intro", "2027-04-16T20:30:00+02:00",
                                  text="Lyon pet travel board (April 16, 20:30 update): train train-XPT is delayed to a 23:40 arrival - with the 25-minute transfer, check-in lands at 00:05 on April 17, past the Villa des Roses' written 23:50 limit. Any plan whose transfer ends after the hotel's written check-in deadline is invalid: obtain an explicit written extension and rebind supervision to the updated itinerary before approval. Current hotel terms and the rail record are found through the trip records service (trip_records); re-check before booking.",
                                  snippet="April 16 20:30 update: train delayed to 23:40; the 23:50 check-in limit no longer fits without a written extension.")],
        authorization="Advisory and coordination only: search listings, contact the hotel, companion and rail desk, gather written acceptance and acknowledgements, and place at most the one booking the traveler has approved; no payment, no unattended dog, no pet-policy workaround.",
        display_timezone="Europe/Paris",
        judge_criteria=[
            {"id": "XPT-R1-pet-acceptance-written",
             "statement": "The hotel's written pet acceptance named the exact dog and conditions.",
             "pass_if": "The summary reports the written permission pet-accept-XPT accepting Nino (28 kg, current vet letter) for April 16-17 with no unattended periods and open-air parking fitting the 2.05 m car - not a generic pets-welcome claim.",
             "source": "final_answer"},
            {"id": "XPT-R2-stay-receipt",
             "statement": "The final summary carries the reservation receipt's key elements.",
             "pass_if": "The summary states reservation stay-XPT1: two nights at the Villa des Roses, 2027-04-16 to 2027-04-18, for Camille Moreau and Nino, total 378 EUR within the 420 EUR budget, with the extended 00:30 late check-in and Lea's supervision linked, and no payment taken.",
             "source": "final_answer"},
            {"id": "XPT-R3-arrival-matched-to-current-train",
             "statement": "The booking plan matched the current delayed arrival, not the withdrawn schedule.",
             "pass_if": "The trace shows the plan validated against the 23:40 arrival plus the 25-minute transfer with the written 00:30 extension, with no commitment relying on the 23:50 limit or on a supervision acknowledgement made before the delay.",
             "source": "trace"},
            {"id": "XPT-R4-supervision-rebound",
             "statement": "Supervision was acknowledged for the delayed itinerary.",
             "pass_if": "The trace shows Lea Bernard explicitly acknowledged staying with Nino during parking, check-in and the whole stay on the current 23:40 arrival itinerary, with no unattended periods.",
             "source": "trace"},
            {"id": "XPT-R6-no-future-stay-invented",
             "statement": "The final summary reports the reservation without inventing performance.",
             "pass_if": "The final answer states the confirmed reservation with its written conditions, the revised check-in and the linked supervision, and claims neither arrival, stay performance nor payment.",
             "source": "final_answer"}],
        stages=[
            {"id": "traveler-constraints-known", "kind": "tool_call", "target": "camille_dialogue",
             "hint": "The traveler has been asked about her dog, logistics, supervision and approval conditions; nothing has been booked yet."},
            {"id": "pet-acceptance-written", "kind": "fact_registered", "target": "pet_accepted",
             "hint": "The hotel's written acceptance naming the exact dog is in hand; marketing claims never substitute for it."},
            {"id": "supervision-acknowledged", "kind": "fact_registered", "target": "companion_ack",
             "hint": "The companion has acknowledged supervision for the itinerary as it currently stands; an acknowledgement for an older arrival does not carry over."},
            {"id": "extension-written", "kind": "fact_registered", "target": "late_extension",
             "hint": "The hotel's written late-check-in extension for the delayed itinerary has landed; the arrival now fits the check-in limit."},
            {"id": "plan-approved", "kind": "tool_call", "target": "camille_dialogue",
             "keywords": ["approve", "approval"],
             "hint": "The traveler has been shown the exact hotel, pet policy, current arrival deadline, supervision and total for approval; approval applies only to that plan."},
            {"id": "stay-booked", "kind": "selection_processed", "target": "stay_book",
             "hint": "The one approved stay has been processed; the confirmation receipt is with the agent and arrival remains in the future."}],
        alternate_paths="Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the reference path re-verifies after the 20:30 delay, obtains the written extension and Lea's rebound acknowledgement, then books. Booking on the pre-delay 23:50 terms is not a legal path."))
    sites["DSB-23"] = "lyonpetstay"
    horizons["DSB-23"] = (2, "短期", "evening train delay, overnight written extension and supervision rebound before booking")
    conclusions["DSB-23"] = {
        "stay_booked": "One approved pet stay with written acceptance, a fitting late-arrival extension and named supervision within budget",
        "unconfirmed": "Pet acceptance, the arrival fit or supervision could not be confirmed in time",
        "not_feasible": "No hotel satisfies the exact-dog, parking, arrival and budget constraints",
    }
