"""DSB-36 <- LATCH case leisure-step-free-festival-evening-001 (accessible
festival evening). One family outing: three free seated step-free access
places for the correct 21:00 Pancho Libre set, a step-free bus round trip,
and a midday ferry lift outage that invalidates the alternative route."""

LATCH_CASE = "leisure-step-free-festival-evening-001"


def build(A, tasks, sites, horizons, conclusions):
    # ---- DSB-36 <- LATCH leisure-step-free-festival-evening-001 -------------
    # The LATCH festival.search becomes a hidden kind="catalog" tool
    # (festival_search): six show listings (stale prior-year paid listing,
    # wrong-time set, other artists, too-late fireworks) plus the three route
    # rows. The L-OFFICIAL event (10:20: official show confirmation plus the
    # three-seat access offer) becomes a catalog update replacing the pending
    # listing with the confirmed row and adding the offer row; the L-LIFT
    # event (12:40 ferry lift outage) becomes a second update plus a page
    # rewrite. The LATCH access.reserve becomes a hidden kind="select" tool
    # (reserve_access) bound to the catalog; only the offer row is acceptable.
    # The LATCH user.dialogue becomes a hidden kind="dialogue" tool
    # (family_dialogue): the sparse prompt's access, travel and authorization
    # facts never appear on any page, only by asking. The case deadline
    # (July 31 17:00, 7h after start) is shorter than the >= 2-day horizon DSB
    # validation requires, so the deadline moves to Aug 2 17:00 Halifax time;
    # every case event stays inside the window.
    fact = A["fact"]; lookup = A["lookup"]; document = A["document"]
    acknowledge = A["acknowledge"]; reply = A["reply"]
    workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; hidden_tool = A["hidden_tool"]
    page_update = A["page_update"]

    f = {
        "show_start": fact("21:00",
                           "The current official Pancho Libre set (l02 v2) starts at 21:00 at the Maritime Museum stage and ends at 21:35."),
        "stage": fact("Maritime Museum",
                      "The current 21:00 Pancho Libre set plays the Maritime Museum stage, not the prior-year Pier stage."),
        "show_end": fact("21:35",
                         "The current official set ends at 21:35, leaving the 21:50 return bus feasible."),
        "route_step_free": fact(True,
                                "The reserved bus-L route is step-free on every leg: outbound 20:00-20:20 with an eight-minute walk, standing stretches at most seven minutes, and return departing 21:50 after an eight-minute walk from the stage."),
        "home_arrival": fact("22:15",
                             "The bus-L return arrives 22:10 with a five-minute walk home, reaching home by 22:15 - inside the requirement."),
        "bus_fare": fact(18,
                         "The step-free bus-L round trip costs 18 CAD for the three-person family."),
        "total_cost": fact(108,
                           "The full family plan is 108 CAD: admission 0 (free) + transport 18 + food 60 + contingency 30, within the 360 CAD cap."),
        "access_reserved": fact(True,
                                "Three free seated step-free access places for the 21:00 set have been confirmed with check-in from 20:30 to 20:45; no payment was taken."),
        "seats": fact(3,
                      "Three seated access places are confirmed for the family (Wei, Mei and Lila)."),
    }
    a = [
        person("access_desk", "Harbour Festival access desk·Priya Nair",
               "festival accessibility, seated viewing and step-free route records", "halifax_daily",
               [workflow("Seated access and step-free route status",
                         ["access", "seats", "seated", "step-free", "wheelchair", "bus", "route", "accessibility", "festival"],
                         [],
                         [acknowledge(business(20)),
                          lookup(["seats", "route_step_free", "bus_fare"], business(60),
                                 "check seated viewing capacity and step-free route status"),
                          document(["seats", "route_step_free", "bus_fare"], business(20)),
                          reply()])],
               "Confirms seated step-free viewing capacity and the step-free bus route in writing; festival admission is free and prior-year paid ticket listings are stale; access places are reserved through the desk named on the entry page."),
    ]
    # The access desk attests the official show record and the reservation
    # through the hidden desks; its mail workflow carries seat and route facts.
    a[0]["knowledge"] = sorted(set(a[0]["knowledge"]) |
                               {"show_start", "stage", "show_end", "home_arrival",
                                "total_cost", "access_reserved"})
    entries = [
        {"id": "l01", "title": "Pancho Libre - 20:00 Pier (prior year)",
         "text": "A 2026 listing showing a 20:00 Pier set at 189 CAD for the party. Prior-year paid ticket listings are stale: this year's festival admission is free.",
         "fields": {"artist": "Pancho Libre", "start": "20:00", "stage": "Pier", "year": 2026,
                    "ticket_cad": 189, "status": "stale"}},
        {"id": "l02-v1", "title": "Pancho Libre - 21:00 Maritime Museum (pending)",
         "text": "This year's 21:00 set at the Maritime Museum, awaiting official confirmation from the festival access desk.",
         "fields": {"artist": "Pancho Libre", "start": "21:00", "stage": "Maritime Museum",
                    "year": 2027, "version": 1, "status": "awaiting_official_confirmation", "ticket_cad": 0}},
        {"id": "l03", "title": "Pancho Libre - 18:00 Maritime Museum",
         "text": "Same artist and stage at 18:00: not the requested 21:00 set.",
         "fields": {"artist": "Pancho Libre", "start": "18:00", "stage": "Maritime Museum",
                    "year": 2027, "ticket_cad": 0}},
        {"id": "l04", "title": "Seb and Fritz - 20:00 Sackville",
         "text": "A different artist at 20:00 on the Sackville stage.",
         "fields": {"artist": "Seb and Fritz", "start": "20:00", "stage": "Sackville",
                    "year": 2027, "ticket_cad": 0}},
        {"id": "l05", "title": "Family Act - 14:00 Seaport",
         "text": "Free daytime family show at 14:00 on the Seaport stage; the walk from the headline stage is 18 minutes, beyond the family's limit.",
         "fields": {"artist": "Family Act", "start": "14:00", "stage": "Seaport", "year": 2027,
                    "walk_from_headline_minutes": 18, "ticket_cad": 0}},
        {"id": "l06", "title": "Fireworks - 22:00 Harbour",
         "text": "Harbour fireworks at 22:00: too late for the 22:15 home deadline.",
         "fields": {"artist": "Fireworks", "start": "22:00", "stage": "Harbour", "year": 2027,
                    "ticket_cad": 0}},
        {"id": "bus-L", "title": "Accessible bus-L round trip",
         "text": "Step-free accessible bus: outbound 20:00-20:20 with an eight-minute step-free walk to the viewing area, standing stretches at most seven minutes; return walk 21:35-21:43, bus 21:50, arrive 22:10, five-minute walk home (home by 22:15). Roundtrip family fare 18 CAD. Platform opens 20:30; the 20:28 arrival waits two minutes.",
         "fields": {"route": "bus-L", "version": 1, "step_free": True, "stairs": 0,
                    "outbound_depart": "20:00", "walk_to_stage_minutes": 8,
                    "return_depart": "21:50", "return_arrive": "22:10",
                    "home_walk_minutes": 5, "max_standing_minutes": 7,
                    "roundtrip_party_fare_cad": 18},
         "facts": ["route_step_free", "home_arrival", "bus_fare"], "issuer": "access_desk"},
        {"id": "ferry-L", "title": "Ferry-L round trip",
         "text": "Step-free ferry alternative, roundtrip family fare 15 CAD. Lift status can change without notice.",
         "fields": {"route": "ferry-L", "version": 1, "step_free": True, "stairs": 0,
                    "roundtrip_party_fare_cad": 15}},
        {"id": "stairs-shortcut", "title": "Stairs shortcut",
         "text": "A 12-stair shortcut between the ferry terminal and the stage; not step-free.",
         "fields": {"route": "stairs-shortcut", "version": 1, "step_free": False, "stairs": 12}},
    ]
    l02_v2 = {"id": "l02-v2", "title": "Pancho Libre - 21:00 Maritime Museum (confirmed)",
              "text": "Official confirmation: this year's Pancho Libre set starts 21:00 and ends 21:35 at the Maritime Museum stage. Admission is free; seated step-free viewing is reserved through the access desk.",
              "fields": {"artist": "Pancho Libre", "start": "21:00", "end": "21:35",
                         "stage": "Maritime Museum", "year": 2027, "version": 2,
                         "status": "confirmed", "ticket_cad": 0},
              "facts": ["show_start", "stage", "show_end"], "issuer": "access_desk"}
    offer = {"id": "offer-L1", "title": "Access offer - three seated step-free places",
             "text": "Free access offer for the confirmed 21:00 set: three seated step-free places, viewing platform opens 20:30, check-in deadline 20:45, fee 0 CAD. Reserve through the access desk.",
             "fields": {"offer": "offer-L1", "show_id": "l02", "show_version": 2, "seats": 3,
                        "seated": True, "step_free": True, "opens": "20:30",
                        "check_in_deadline": "20:45", "fee_cad": 0}}
    ferry_outage = {"id": "ferry-L-outage", "title": "Ferry-L v2 - lift outage",
                    "text": "The ferry-L lift is out of service; the route is not step-free until repaired. Step-free proposals and route reservations using the ferry are invalidated; the step-free bus-L remains available.",
                    "fields": {"route": "ferry-L", "version": 2, "step_free": False,
                               "status": "lift_outage"}}
    tasks.append(task(
        "DSB-36", "Accessible festival evening: the correct 21:00 set with step-free travel", "leisure_entertainment",
        "2027-07-31T10:00:00-03:00", "2027-08-02T17:00:00-03:00",
        "Plan our three-person family visit to Pancho Libre's 21:00 set on July 31, 2027, in the Halifax test district, total at most 360 CAD. Ask me about access needs, travel and approval; confirm the current official show and step-free seating with the festival, watch for route changes, and reserve only the approved free access places. No purchases or payments.",
        {"date": "2027-07-31", "city": "Halifax test district", "party_size": 3}, [],
        [page("festival-intro", "Harbour Festival Programme",
              "Synthetic festival listings for the Halifax test district: shows, routes and the access desk. Current shows, routes and access offers are found through the festival search service (festival_search); listings and route status can change, so re-check before reserving. The family's constraints can be clarified through the family profile desk (family_dialogue). Official show confirmation and free seated access come from the festival access desk.",
              [], "Halifax festival show listings, step-free routes and the access desk."),
         page("festival-contacts", "Festival access contacts",
              "The Harbour Festival access desk is handled by Priya Nair, who answers daily during business hours.",
              ["access_desk"], "Contact for the Harbour Festival access desk."),
         page("festival-entry", "Festival access reservation desk",
              "Free seated access places are reserved through the festival access desk (reserve_access): confirm the current official show through festival_search, agree the stage, step-free route, seats and budget with the family, then request the three places. At most one reservation; festival admission is free; no purchases, payments or alcohol packages.",
              [], "Festival access desk: current show, step-free route, organizer approval, three free places.")],
        f, a,
        [goal("show_start", "21:00", "show_start"),
         goal("stage", "Maritime Museum", "stage"),
         goal("show_end", "21:35", "show_end"),
         goal("route_step_free", True, "route_step_free"),
         goal("home_arrival", "22:15", "home_arrival"),
         goal("total_cost", 108, "total_cost"),
         goal("access_reserved", True, "access_reserved"),
         goal("seats", 3, "seats")],
        "access_confirmed",
        [{"op": "visit_page", "page": "festival-contacts"},
         {"op": "discover", "name": "family_dialogue"},
         {"op": "tool", "name": "family_dialogue", "args": {"question": "What are the access needs, travel constraints, budget and approval arrangements for the festival visit?"}},
         {"op": "discover", "name": "festival_search"},
         {"op": "tool", "name": "festival_search", "args": {"query": "Pancho Libre"}},
         {"op": "advance", "at": "2027-07-31T10:25:00-03:00"},
         {"op": "tool", "name": "festival_search", "args": {"query": "Pancho Libre access"}},
         {"op": "tool", "name": "festival_search", "args": {"query": "bus route"}},
         send("access_desk", "Please confirm seated step-free viewing capacity and the step-free bus route for our family of three", "verify"),
         wait("verify"),
         {"op": "advance", "at": "2027-07-31T13:30:00-03:00"},
         {"op": "tool", "name": "festival_search", "args": {"query": "route"}},
         {"op": "tool", "name": "family_dialogue", "args": {"question": "Do you approve the exact plan: 21:00 Maritime Museum set, bus-L step-free round trip, three seated places, 108 CAD total?"}},
         {"op": "discover", "name": "reserve_access"},
         {"op": "tool", "name": "reserve_access", "args": {"entry": "offer-L1"}},
         {"op": "advance", "at": "2027-07-31T15:00:00-03:00"},
         {"op": "tool", "name": "reserve_access", "args": {"query": "status"}}],
        ["official show confirmation and access offer appear mid-morning",
         "ferry lift outage at midday invalidates the step-free alternative",
         "prior-year paid ticket listing is stale; admission is free",
         "search-discoverable show and route inventory",
         "sparse prompt: family constraints only surface through dialogue",
         "hidden access desk revalidates the live offer"],
        ["trusting the stale 2026 paid Pier listing",
         "reserving the 18:00 wrong-time set or another artist",
         "using the ferry after the lift outage or the 12-stair shortcut",
         "booking the 22:00 fireworks with no feasible return",
         "paying for admission or adding an alcohol package",
         "reserving before the organizer approves the exact plan"],
        extra_tools=("check_schedule",),
        hidden_tools=(
            hidden_tool("festival_search",
                        "Harbour Festival search. Argument: query (optional string), e.g. \"Pancho Libre\" or \"bus route\". Returns current show listings, routes and access offers; rows can appear, change or disappear, so re-check before reserving.",
                        "catalog",
                        {"keywords": ["festival", "show", "concert", "pancho", "stage", "access", "halifax"],
                         "clue": "A festival search service named festival_search lists the current shows, routes and access offers.",
                         "entries": entries,
                         "updates": [
                             {"at": "2027-07-31T10:20:00-03:00", "remove": ["l02-v1"],
                              "add": [l02_v2, offer]},
                             {"at": "2027-07-31T12:40:00-03:00", "remove": ["ferry-L"],
                              "add": [ferry_outage]}]}),
            hidden_tool("reserve_access",
                        "Festival access reservation desk. Argument: {\"entry\": listing_id} to request the three free seated step-free places shown in one current festival_search row, or {\"query\": text} to read back the current reservation status. Reserve only the plan the organizer has approved; at most one reservation; no payment is taken.",
                        "select",
                        {"catalog": "festival_search", "expect_entry": "offer-L1", "expect": {"seats": 3},
                         "process_delay": 30, "calendar": "halifax_daily",
                         "result_text": "Access confirmed: three free seated step-free places for the confirmed 21:00 Pancho Libre set at the Maritime Museum stage, viewing platform opens 20:30, check-in by 20:45, fee 0 CAD. Full plan 108 CAD (admission 0, transport 18, food 60, contingency 30). No payment taken.",
                         "reject_text": "The requested offer is no longer current or does not match an approvable plan; nothing was reserved.",
                         "facts": ["access_reserved", "total_cost"], "issuer": "access_desk",
                         "page_update": {"page": "festival-entry",
                                         "snippet": "Festival access desk: an approved access request is being processed; check the desk status for the outcome."}}),
            hidden_tool("family_dialogue",
                        "Ask the family organizer, Mei Chen, one question. Argument: {\"question\": text}. She answers only what is explicitly asked and does not volunteer other facts.",
                        "dialogue",
                        {"persona": "Mei Chen (family organizer). Cheerful but meticulous about Wei's access needs: she answers exactly what is asked, keeps the no-stairs and walking limits front of mind, and approves only the current stage, route, seats and budget shown to her.",
                         "dialogue_mode": "llm",
                         "rules": [
                             {"keywords": ["access", "wei", "stairs", "wheelchair", "walk", "standing", "seats", "seat"],
                              "answer": "Wei needs no stairs, walking segments at most twelve minutes and standing stretches at most twenty-five minutes, with confirmed seats. Lila is eight; no alcohol package."},
                             {"keywords": ["travel", "bus", "ferry", "route", "home", "return", "when", "leave"],
                              "answer": "We travel from home-L and must be back by 22:15. Prefer the accessible bus. Festival admission is free; paid prior-year ticket listings are stale."},
                             {"keywords": ["budget", "cost", "price", "total", "money", "food"],
                              "answer": "Total at most 360 CAD including travel, food and contingency. The current plan is 108 CAD: admission 0, transport 18, food 60, contingency 30."},
                             {"keywords": ["approve", "approval", "permission", "confirm", "review"],
                              "answer": "Show me the current stage, route, seats and budget for approval before reserving the free access places. No purchases or payments."},
                             {"keywords": ["show", "time", "artist", "pancho", "set", "date"],
                              "answer": "The three-person family visit is for Pancho Libre's 21:00 set on July 31, 2027."}],
                         "default": "Please ask me about access needs, travel, budget or approval."}),
        ),
        page_updates=[page_update("festival-intro", "2027-07-31T12:40:00-03:00",
                                  snippet="July 31 midday update: the ferry-L lift is out of service; the ferry is not step-free until repaired. The step-free bus-L remains available.")],
        authorization="Advisory and coordination only: search listings, verify the current show and step-free routes, and reserve at most the approved free access places; no purchases, payments or alcohol packages.",
        display_timezone="America/Halifax",
        judge_criteria=[
            {"id": "L-R1-current-show",
             "statement": "The plan follows the current official show, not the stale listings.",
             "pass_if": "The summary carries the official confirmation's key elements: the 21:00 Pancho Libre set at the Maritime Museum stage ending 21:35 with free admission - not the prior-year paid Pier listing, the 18:00 set or another artist.",
             "source": "final_answer"},
            {"id": "L-R2-accessible-journey",
             "statement": "The reported journey is accessible end to end.",
             "pass_if": "The trace or final answer reports step-free legs throughout, walks at most twelve minutes, standing at most twenty-five minutes, confirmed seats and a feasible 20:30-20:45 check-in, without relying on the ferry after the outage.",
             "source": "trace"},
            {"id": "L-R6-no-attendance-claim",
             "statement": "The final summary claims no attendance or purchase.",
             "pass_if": "The final answer states the confirmed three seated places, the current show and the step-free bus plan with home by 22:15, describes remaining travel as future, and claims neither attendance, purchase, nor payment.",
             "source": "final_answer"}],
        stages=[
            {"id": "family-consulted", "kind": "tool_call", "target": "family_dialogue",
             "hint": "The family's constraints are known: no stairs, walks at most twelve minutes, standing at most twenty-five minutes, confirmed seats, home by 22:15, total at most 360 CAD."},
            {"id": "show-confirmed", "kind": "fact_registered", "target": "show_start",
             "hint": "The official confirmation is in: the 21:00 Pancho Libre set at the Maritime Museum stage, ending 21:35, admission free; the prior-year paid listing is stale."},
            {"id": "plan-approved", "kind": "tool_call", "target": "family_dialogue",
             "keywords": ["approve", "approval"],
             "hint": "The organizer has approved the exact plan - current stage, step-free route, three seated places and budget; approval covers reserving those free places only."},
            {"id": "access-reserved", "kind": "selection_processed", "target": "reserve_access",
             "hint": "The three approved free seated step-free places have been reserved from the live offer; the confirmation is read back through the access desk."}],
        alternate_paths="Any legal order of dialogue, desk mail and searches is accepted if every goal's evidence conditions hold; choosing the ferry before the outage then switching to the bus after it is a legal alternative, but the scored answer keys follow the step-free bus plan."))
    sites["DSB-36"] = "harbourfestival"
    horizons["DSB-36"] = (2, "短期", "official show confirmation plus midday ferry lift outage")
    conclusions["DSB-36"] = {
        "access_confirmed": "Three free seated step-free places confirmed with a feasible step-free return",
        "unconfirmed": "The current show or step-free route could not be verified in time",
        "not_feasible": "No current show, seating or step-free route satisfies the constraints",
    }
