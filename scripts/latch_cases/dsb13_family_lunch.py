"""DSB-13 <- LATCH case food-family-lunch-001 (Garden Ramp Bistro lunch).
One family lunch reservation with verified step-free access, written sesame
cross-contact controls, a mid-episode offer rewrite, and one approved commit."""

LATCH_CASE = "food-family-lunch-001"


def build(A, tasks, sites, horizons, conclusions):
    # ---- DSB-13 <- LATCH food-family-lunch-001 ------------------------------
    # One family lunch reservation with verified access and written sesame
    # controls. The LATCH dining-directory search becomes a hidden kind="catalog"
    # tool (restaurant_search, discoverable via web_search keywords), whose
    # inventory carries the six noisy listings; the F-OFFER event (13:00 six-top
    # gone, offer v2 at 13:30 / 247.80) becomes a catalog `updates` entry plus a
    # page_update at 2027-07-10T10:00 New York time. The LATCH reservation.create
    # becomes a hidden kind="select" tool (reserve_table) linked to the catalog:
    # only the refreshed r101-v2 row is acceptable, and acceptance issues the
    # written reservation evidence. The LATCH user.dialogue becomes a hidden
    # kind="dialogue" tool (family_dialogue): the sparse prompt's party/access/
    # diet/limits/authorization facts never appear on any page, only by asking.
    # Provider managers keep the DSB mail surface: the Garden manager verifies
    # access + sesame cross-contact controls in writing (the F-CONTROLS reply),
    # the Harbor manager is the already-verified alternative. The case deadline
    # (Jul 10 17:00) is 32h after start; DSB validation requires a >= 2-day
    # horizon, so the deadline moves to Jul 11 12:00 New York time — the case's
    # own free-cancellation boundary and still before the lunch.
    fact = A["fact"]; lookup = A["lookup"]; document = A["document"]
    acknowledge = A["acknowledge"]; reply = A["reply"]; suggest = A["suggest"]
    deny = A["deny"]; refer = A["refer"]; workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; hidden_tool = A["hidden_tool"]
    page_update = A["page_update"]

    f = {
        "address": fact("12 Ramp Lane, Riverdale test district",
                        "The confirmed reservation is at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district."),
        "table_time": fact("13:30",
                           "The reserved table starts at 13:30 New York time on 2027-07-11, inside the 13:00-14:00 start window."),
        "total_cost": fact(247.8,
                           "The current pre-tip total for the six-meal plan is 247.80 USD including tax and mandatory service, within the 280 USD budget."),
        "access": fact(True,
                       "Provider evidence verify-F101 confirms a continuous step-free ramp route to the table at Garden Ramp Bistro; no staff lifting and no cobblestone-only entrance."),
        "controls": fact(True,
                         "Written provider controls for menu-101 v1: no sesame ingredients in the selected dishes, separate cleaned utensils and preparation space, and a flagged allergy ticket, with no substitutions without a fresh check. These are provider-reported controls, not a medical guarantee."),
        "fish_free": fact(True,
                          "Both child meals (tomato pasta) on menu-101 v1 are prepared without fish."),
        "reserved": fact(True,
                         "One reservation for six at Garden Ramp Bistro on 2027-07-11 at 13:30 has been confirmed with the meal requirements acknowledged; no payment or automatic gratuity was taken."),
        # Already-verified alternative path (LATCH r106): legal but later and
        # pricier than the refreshed r101 offer; kept as actor knowledge only.
        "harbor_address": fact("6 Harbor Lane, Riverdale test district",
                               "Harbor Family Table is located at 6 Harbor Lane, Riverdale test district."),
        "harbor_time": fact("13:45",
                            "Harbor Family Table offers a six-top at 13:45 on 2027-07-11."),
        "harbor_total": fact(259.6,
                             "The Harbor Family Table pre-tip total is 259.60 USD including tax and mandatory service."),
        "harbor_verified": fact(True,
                                "Provider evidence verify-F106 (valid until 2027-07-11 14:00 New York time) confirms a step-free table route and written sesame controls for Harbor Family Table's menu-106 v1."),
    }
    a = [
        person("garden_manager", "Garden Ramp Bistro manager·Alex Chen",
               "provider verification, exact menu quotes and reservations", "us_eastern_daily",
               [workflow("Access and sesame verification",
                         ["access", "wheelchair", "sesame", "allergy", "verification", "verify", "controls", "step-free", "menu"],
                         [],
                         [acknowledge(business(30)),
                          lookup(["access", "controls", "fish_free"], business(180),
                                 "check the room-to-table route and kitchen controls"),
                          document(["access", "controls", "fish_free"], business(30)),
                          reply()]),
                 workflow("Current table offer",
                          ["offer", "quote", "price", "total", "table", "time", "cost"],
                          [],
                          [lookup([], business(60), "check the current published table offer"),
                           reply()], id="offer")],
               "Confirms the actual entrance, selected dishes, preparation controls, table time and price in writing; table offers can change without notice; reservations go through the reservation desk named on the entry page."),
        person("harbor_manager", "Harbor Family Table manager·Robin Diaz",
               "confirmed alternative restaurant status", "us_eastern_daily",
               [workflow("Harbor status and quote",
                         ["harbor", "verified", "alternative", "status"],
                         [],
                         [lookup(["harbor_address", "harbor_time", "harbor_total", "harbor_verified"], business(60)),
                          document(["harbor_address", "harbor_time", "harbor_total", "harbor_verified"], business(30)),
                          reply()])],
               "Only confirms the r106 menu and reservation terms; access and allergen evidence already verified (verify-F106)."),
    ]
    # The Garden manager attests the reservation facts (reserved table, address,
    # time and current total) but never issues them through a mail workflow:
    # the only issuance channel is the hidden reservation desk (reserve_table).
    a[0]["knowledge"] = sorted(set(a[0]["knowledge"]) | {"reserved", "address", "table_time", "total_cost"})
    entries = [
        {"id": "r101-v1", "title": "Garden Ramp Bistro - six-top at 13:00 (offer v1)",
         "text": "Step-free ramp entrance; written room-to-table check pending manager verification. Menu v1: four adult roast chicken, two child tomato pasta (fish-free); no declared sesame ingredients.",
         "fields": {"restaurant": "Garden Ramp Bistro", "address": "12 Ramp Lane, Riverdale test district",
                    "party_size": 6, "start": "13:00", "offer_version": 1,
                    "subtotal_usd": 200.00, "tax_usd": 16.00, "service_usd": 20.00, "total_usd": 236.00},
         "expires_at": "2027-07-10T10:00:00-04:00"},
        {"id": "r102", "title": "Garden - 88 Step Street",
         "text": "Same display name, different address and operator. One entrance step and no ramp; the listing claims staff can lift a wheelchair.",
         "fields": {"restaurant": "Garden (Step Street)", "address": "88 Step Street, Riverdale test district",
                    "party_size": 6, "entrance_steps": 1, "ramp": False, "total_usd": 210.00}},
        {"id": "r103", "title": "Sesame Wok",
         "text": "Step-free entrance, but selected dishes use sesame oil and shared preparation cannot meet the requested sesame controls.",
         "fields": {"restaurant": "Sesame Wok", "address": "3 Market Row, Riverdale test district",
                    "party_size": 6, "entrance_steps": 0, "ramp": True, "total_usd": 190.00}},
        {"id": "r104", "title": "Small Courtyard",
         "text": "Step-free but a cobblestone-only entrance, and the courtyard seats at most four.",
         "fields": {"restaurant": "Small Courtyard", "address": "4 Courtyard Row, Riverdale test district",
                    "party_size": 4, "entrance_steps": 0, "ramp": True, "cobblestone_only": True, "total_usd": 220.00}},
        {"id": "r105", "title": "Sunday Hall",
         "text": "Step-free and six seats, but closed for a private event on 2027-07-11; the listing is stale.",
         "fields": {"restaurant": "Sunday Hall", "address": "5 Hall Lane, Riverdale test district",
                    "party_size": 6, "entrance_steps": 0, "ramp": True, "available": False, "total_usd": 260.00}},
        {"id": "r106", "title": "Harbor Family Table - six-top at 13:45",
         "text": "Step-free table route and written sesame controls already verified (verify-F106, valid until 2027-07-11 14:00). Menu v1: four adult vegetable rice, two child pasta (fish-free).",
         "fields": {"restaurant": "Harbor Family Table", "address": "6 Harbor Lane, Riverdale test district",
                    "party_size": 6, "start": "13:45", "offer_version": 1,
                    "subtotal_usd": 220.00, "tax_usd": 17.60, "service_usd": 22.00, "total_usd": 259.60}},
    ]
    r101_v2 = {"id": "r101-v2", "title": "Garden Ramp Bistro - six-top at 13:30 (offer v2)",
               "text": "The unreserved 13:00 six-top is gone. Same menu v1 and delivered controls (verify-F101) remain available at 13:30 with the revised price. This is a live offer, not a confirmed booking.",
               "fields": {"restaurant": "Garden Ramp Bistro", "address": "12 Ramp Lane, Riverdale test district",
                          "party_size": 6, "start": "13:30", "offer_version": 2,
                          "subtotal_usd": 210.00, "tax_usd": 16.80, "service_usd": 21.00, "total_usd": 247.80}}
    tasks.append(task(
        "DSB-13", "Family lunch: verified access, sesame controls and a changed offer", "food_dining",
        "2027-07-09T09:00:00-04:00", "2027-07-11T12:00:00-04:00",
        "Arrange Sunday lunch for six on July 11, 2027, in the Riverdale test district. Ask me about the party, accessibility, food requirements, budget and permission before reserving; verify wheelchair access and written sesame controls with the restaurant, watch for offer changes, and make at most one approved reservation. No payment or automatic gratuity.",
        {"date": "2027-07-11", "area": "Riverdale test district", "party_size": 6}, [],
        [page("dining-intro", "Riverdale Dining Directory",
              "Synthetic restaurant listings for the Riverdale test district; listing claims alone do not establish access or allergen controls. Current listings, table times and prices are found through the directory's restaurant search service (restaurant_search), and offers can be revised or withdrawn mid-week, so an earlier result may go stale. Family requirements can be clarified through the family profile desk (family_dialogue). Written access and sesame-control confirmations come from the restaurants themselves by mail.",
              [], "Riverdale test district lunch listings, table offers and family requirements desk."),
         page("dining", "Riverdale dining contacts",
              "Garden Ramp Bistro (12 Ramp Lane) is handled by its manager, Alex Chen; the already-verified Harbor Family Table (6 Harbor Lane) is handled by manager Robin Diaz. Both answer daily during business hours.",
              ["garden_manager", "harbor_manager"], "Contacts for the Garden Ramp Bistro and Harbor Family Table managers."),
         page("dining-entry", "Garden Ramp Bistro reservation desk",
              "Reservations for Garden Ramp Bistro are placed through the bistro's reservation desk (reserve_table): pick one current restaurant_search listing, obtain the family organizer's approval of the exact plan (address, table time, six meals, written controls, full pre-tip cost) after July 10 at 11:00 New York time, then request that one table. At most one reservation; no payment or automatic gratuity. Stale offers are revalidated against live listings at booking time.",
              [], "Garden Ramp Bistro reservation desk: current listing, organizer approval, one table, no payment.")],
        f, a,
        [goal("restaurant_address", "12 Ramp Lane, Riverdale test district", "address"),
         goal("table_time", "13:30", "table_time"),
         goal("total_cost", 247.8, "total_cost"),
         goal("access_verified", True, "access"),
         goal("sesame_controls_written", True, "controls"),
         goal("child_meals_fish_free", True, "fish_free"),
         goal("reservation_confirmed", True, "reserved")],
        "reserved_verified",
        [{"op": "visit_page", "page": "dining"},
         {"op": "discover", "name": "family_dialogue"},
         {"op": "tool", "name": "family_dialogue", "args": {"question": "What are the party size, accessibility needs, food requirements, budget and approval arrangements for the lunch?"}},
         send("garden_manager", "Please verify step-free wheelchair access and written sesame controls for our party of six", "verify"),
         wait("verify"),
         {"op": "discover", "name": "restaurant_search"},
         {"op": "tool", "name": "restaurant_search", "args": {"query": "Riverdale lunch six people"}},
         {"op": "advance", "at": "2027-07-10T10:30:00-04:00"},
         {"op": "tool", "name": "restaurant_search", "args": {"query": "Garden Ramp Bistro"}},
         {"op": "discover", "name": "reserve_table"},
         {"op": "tool", "name": "reserve_table", "args": {"entry": "r101-v2"}},
         {"op": "advance", "at": "2027-07-10T14:00:00-04:00"},
         {"op": "tool", "name": "reserve_table", "args": {"query": "reservation"}}],
        ["Mid-episode offer rewrite removes the 13:00 table", "written verification turnaround by mail",
         "organizer approval window opens July 10 at 11:00", "search-discoverable directory inventory",
         "hidden reservation desk revalidates the live listing", "noisy directory access claims",
         "sparse prompt: family facts only surface through dialogue"],
        ["trusting a directory access claim without provider evidence",
         "booking the stale 13:00 offer after it is gone",
         "reserving before the organizer approves the exact plan",
         "accepting a sesame-free label without cross-contact controls",
         "counting an optional tip inside the 280 USD budget",
         "booking an ineligible listing (steps, sesame oil, cobblestone-only, closed, capacity four)",
         "confusing the two Garden records (12 Ramp Lane vs 88 Step Street)"],
        extra_tools=("check_schedule",),
        hidden_tools=(
            hidden_tool("restaurant_search",
                        "Riverdale dining directory search. Argument: query (optional string), e.g. \"Riverdale lunch six people\" or a restaurant name. Returns the current listings with addresses, table times and pre-tip totals; rows may change or disappear as offers are revised, so re-check before booking.",
                        "catalog",
                        {"keywords": ["lunch", "restaurant", "menu", "dining", "table", "riverdale", "family"],
                         "clue": "A directory search service named restaurant_search lists the current Riverdale lunch table offers.",
                         "entries": entries,
                         "updates": [{"at": "2027-07-10T10:00:00-04:00",
                                      "remove": ["r101-v1"], "add": [r101_v2]}]}),
            hidden_tool("reserve_table",
                        "Garden Ramp Bistro reservation desk. Argument: {\"entry\": listing_id} to request the table shown in one current restaurant_search row, or {\"query\": text} to read back the current reservation status. Reserve only the plan the family organizer has approved; at most one reservation; no payment is taken.",
                        "select",
                        {"catalog": "restaurant_search", "expect_entry": "r101-v2", "expect": {"party_size": 6},
                         "process_delay": 120, "calendar": "us_eastern_daily",
                         "result_text": "Reservation confirmed: Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district, 2027-07-11 at 13:30 New York time, six seats - four adult roast chicken and two fish-free child tomato pasta - with step-free access and written sesame controls acknowledged by the provider; pre-tip total 247.80 USD including tax and mandatory service; no payment taken. The controls are provider-reported, not a medical guarantee.",
                         "reject_text": "The requested listing is no longer current or does not match an approvable plan; the request was returned and nothing was reserved.",
                         "facts": ["reserved", "address", "table_time", "total_cost"], "issuer": "garden_manager",
                         "page_update": {"page": "dining-entry",
                                         "snippet": "Garden Ramp Bistro reservation desk: an approved reservation request is being processed; check the desk status for the outcome."}}),
            hidden_tool("family_dialogue",
                        "Ask the family organizer, David Klein, one question. Argument: {\"question\": text}. He answers only what is explicitly asked and does not volunteer other facts.",
                        "dialogue",
                        {"persona": "David Klein (family organizer), organized and particular about his family's needs: he answers exactly what is asked in plain terms, states requirements precisely, and never approves a plan he has not been shown in full.",
                         "dialogue_mode": "llm",
                         "rules": [
                             {"keywords": ["party", "how many", "people", "adults", "children", "kids", "booking name"],
                              "answer": "Four adults and two children aged six and nine; the booking name is David Klein."},
                             {"keywords": ["wheelchair", "access", "step", "ramp", "entrance"],
                              "answer": "One adult uses a wheelchair: we need a real step-free route to the table. Staff lifting is not acceptable, and a cobblestone-only entrance is not acceptable."},
                             {"keywords": ["sesame", "allergy", "food", "fish", "meal", "diet", "cross-contact", "ingredients"],
                              "answer": "One guest has a sesame allergy: obtain written ingredient and cross-contact controls for the exact menu, and do not infer safety from a menu label. Both child meals must have no fish."},
                             {"keywords": ["budget", "cost", "price", "total", "tip", "money"],
                              "answer": "Stay within 280 USD before any optional tip, including tax and mandatory service. No payment and no automatic gratuity."},
                             {"keywords": ["time", "when", "start", "hour", "date"],
                              "answer": "Sunday, July 11, 2027, starting between 13:00 and 14:00; we prefer the earlier eligible time."},
                             {"keywords": ["approve", "approval", "permission", "confirm", "review"],
                              "answer": "I can review the final plan from July 10 at 11:00 New York time. Show the restaurant address, current table time, six meals, written sesame controls, access evidence and full pre-tip cost. Reserve only after I approve; no payment or automatic gratuity."}],
                         "default": "Please ask me about the party, accessibility, food requirements, timing, budget or permission."}),
        ),
        page_updates=[page_update("dining-intro", "2027-07-10T10:00:00-04:00",
                                  text="Riverdale Dining Directory (July 10 update): Garden Ramp Bistro's unreserved 13:00 six-top is gone; the same menu and delivered controls remain available at 13:30 with a revised pre-tip total of 247.80 USD including tax and mandatory service. Listings, table times and prices are found through the directory's restaurant search service (restaurant_search); offers can be revised or withdrawn, so re-check before booking. Family requirements can be clarified through the family profile desk (family_dialogue). Written access and sesame-control confirmations come from the restaurants themselves by mail.",
                                  snippet="July 10 update: the 13:00 six-top is gone; Garden Ramp Bistro now offers 13:30 at 247.80 USD pre-tip.")],
        authorization="Advisory and coordination only: search listings, contact restaurants, gather written verification, and create at most the one reservation the organizer has approved; no payment, automatic gratuity, or other binding commitment.",
        display_timezone="America/New_York",
        judge_criteria=[
            {"id": "FR1-reservation-receipt",
             "statement": "The final summary carries the reservation receipt's key elements.",
             "pass_if": "The summary states one confirmed reservation at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district, on 2027-07-11 at 13:30 New York time for six, with the pre-tip total 247.80 USD including tax and mandatory service and no payment taken.",
             "source": "final_answer"},
            {"id": "FR2-access-verified",
             "statement": "Step-free access was verified with provider evidence, not a listing claim.",
             "pass_if": "The summary reports the provider's written confirmation (verify-F101) of a continuous step-free ramp route to the table, with no staff lifting and no cobblestone-only entrance, and does not rest the access claim on the directory listing.",
             "source": "final_answer"},
            {"id": "FR3-cross-contact",
             "statement": "The written sesame controls reported for the exact menu cover cross-contact (separate cleaned utensils and preparation space, flagged allergy ticket), not just a sesame-free label.",
             "pass_if": "The trace or final answer shows cross-contact controls were asked about and reported as provider-reported for the exact selected menu, with no unresolved substitution.",
             "source": "trace"},
            {"id": "FR4-refreshed-offer-booked",
             "statement": "The reservation used the refreshed offer, not the withdrawn one.",
             "pass_if": "The trace shows the agent re-checked the directory after the July 10 change and booked the 13:30 offer v2 at 247.80 USD, never the withdrawn 13:00 offer at 236.00 USD.",
             "source": "trace"},
            {"id": "FR5-child-meals-fish-free",
             "statement": "The child meals are reported as fish-free.",
             "pass_if": "The summary states both child meals (tomato pasta) are prepared without fish, matching the provider's written confirmation.",
             "source": "final_answer"},
            {"id": "FR6-no-safety-guarantee",
             "statement": "The final summary is accurate and does not guarantee medical safety.",
             "pass_if": "The final answer states the actual address, table time, total and acknowledged meal requirements, describes the controls as provider-reported rather than zero risk, and claims neither attendance nor payment.",
             "source": "final_answer"}],
        stages=[
            {"id": "family-requirements-known", "kind": "tool_call", "target": "family_dialogue",
             "hint": "The family organizer has been asked about the party, accessibility, food requirements, budget and approval rules; nothing was reserved yet."},
            {"id": "access-verified", "kind": "fact_registered", "target": "access",
             "hint": "The Garden manager's written verification of the step-free route has landed; the access claim now rests on provider evidence, not the listing."},
            {"id": "offer-refreshed", "kind": "tool_call", "target": "restaurant_search",
             "hint": "The directory has been re-checked and the current live offer is in the agent's hands; earlier rows may have gone stale."},
            {"id": "reservation-confirmed", "kind": "selection_processed", "target": "reserve_table",
             "hint": "The one approved reservation request has been processed; the confirmation receipt is with the agent and nothing further was booked."}],
        alternate_paths="Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the reference path refreshes the Garden offer after the July 10 change, and the already-verified Harbor Family Table is a legal alternative, but the scored answer keys follow the refreshed Garden plan."))
    sites["DSB-13"] = "riverdale"
    horizons["DSB-13"] = (2, "短期", "mid-episode offer rewrite plus organizer approval window")
    conclusions["DSB-13"] = {
        "reserved_verified": "One approved reservation with verified access and written sesame controls within budget",
        "unconfirmed": "Access or controls could not be verified in time",
        "not_feasible": "No listing satisfies the hard constraints",
    }
