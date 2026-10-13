"""DSB-37 <- LATCH case mobility-bicycle-disruption-recovery-001 (cancelled
rail journey with a folded bicycle). One approved replacement: the Mereoak
coach with its timed local transfer, accompanied folded-bike acceptance on
both legs, and a mid-window rail delay that rules out the rail alternative."""

LATCH_CASE = "mobility-bicycle-disruption-recovery-001"


def build(A, tasks, sites, horizons, conclusions):
    # ---- DSB-37 <- LATCH mobility-bicycle-disruption-recovery-001 -----------
    # The LATCH journey.search becomes a hidden kind="catalog" tool
    # (journey_search): the disruption alerts (current cancellation, superseded
    # all-clear) plus six recovery candidates. The MOB-DELAY event (15:05: m01
    # rail arrival slips to 19:51) becomes a catalog update replacing the rail
    # row; the MOB-BIKE event (15:08: accompanied-folded-bike acceptance for
    # m02) becomes an additional row that only appears from that time. The
    # LATCH replacement.reserve becomes a hidden kind="select" tool
    # (reserve_replacement) bound to the catalog; only the m02 coach row is
    # acceptable, and acceptance issues the written recovery evidence. The
    # LATCH user.dialogue becomes a hidden kind="dialogue" tool
    # (traveler_dialogue): the sparse prompt's bike, ticket and authorization
    # facts never appear on any page, only by asking. The case window is 50
    # minutes (14:30 to the 15:20 transfer cutoff); DSB validation requires a
    # >= 2-day horizon, so the deadline moves to Oct 9 15:20 London time while
    # every case event stays inside the window.
    fact = A["fact"]; lookup = A["lookup"]; document = A["document"]
    acknowledge = A["acknowledge"]; reply = A["reply"]
    workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; hidden_tool = A["hidden_tool"]
    page_update = A["page_update"]

    f = {
        "arrival": fact("19:00",
                        "The reserved replacement (m02 coach) departs Mereoak 15:30 and arrives Bristol Temple Meads 19:00, inside the 19:30 deadline."),
        "extra_cost": fact(18,
                           "The complete replacement bundle costs 18 GBP extra: coach fare 14 + local transfer 4 + bicycle fee 0, at the maximum allowed outlay."),
        "bike_accompanied": fact(True,
                                 "Provider evidence bike-MOB1 confirms both the local transfer and the coach accept the folded Brompton kept with the passenger, with no unattended storage and no extra bike fee."),
        "replacement_reserved": fact(True,
                                     "One replacement bundle (coach plus local transfer entitlement, accompanied folded bike accepted) has been confirmed; no payment was taken."),
        "transfer_depart": fact("15:10",
                                "The local transfer departs Reading 15:10 and reaches Mereoak 15:20, giving a ten-minute boarding buffer before the 15:30 coach."),
        "return_preserved": fact(True,
                                 "The original return leg of ticket T-MOB is preserved unchanged; no compensation claim was made and no payment was taken."),
    }
    a = [
        person("rail_desk", "Rail recovery desk·Tom Ashby",
               "disruption records, bike policy and replacement reservations", "london_daily",
               [workflow("Bike policy confirmation",
                         ["bike", "brompton", "folded", "bicycle", "policy", "accompan"],
                         [],
                         [acknowledge(business(10)),
                          lookup(["bike_accompanied"], business(20),
                                 "check accompanied folded-bike acceptance for the transfer and coach"),
                          document(["bike_accompanied"], business(10)),
                          reply()])],
               "Confirms accompanied folded-bike acceptance in writing; live journey inventory and reservations go through the search service and booking desk named on the entry page."),
    ]
    # The rail desk attests the reserved bundle through the hidden desk; its
    # mail workflow carries the bike policy confirmation.
    a[0]["knowledge"] = sorted(set(a[0]["knowledge"]) |
                               {"arrival", "extra_cost", "replacement_reserved",
                                "transfer_depart", "return_preserved"})
    entries = [
        {"id": "alert-cancel-v3", "title": "Alert: service 1C27 cancelled (v3, authoritative)",
         "text": "Current authoritative disruption record: service 1C27 is cancelled. Supersedes all earlier alerts.",
         "fields": {"service": "1C27", "version": 3, "status": "cancelled", "authoritative": True}},
        {"id": "alert-all-clear-v2", "title": "Alert: service 1C27 restored (v2, superseded)",
         "text": "An earlier all-clear claiming 1C27 was restored; superseded by the authoritative cancellation and no longer valid.",
         "fields": {"service": "1C27", "version": 2, "status": "restored",
                    "authoritative": False, "superseded": True}},
        {"id": "m01-v1", "title": "m01 rail recovery - 15:25",
         "text": "Direct rail recovery from Reading departing 15:25, arriving 18:50, no extra fare; folded-bike policy pending confirmation.",
         "fields": {"route": "m01", "version": 1, "mode": "rail", "depart": "15:25",
                    "arrive": "18:50", "extra_gbp": 0, "bike_policy": "pending"}},
        {"id": "m02", "title": "m02 coach via Mereoak - 15:30",
         "text": "Coach from Mereoak to Bristol Temple Meads: local transfer departs Reading 15:10, arrives Mereoak 15:20 (ten-minute boarding buffer), coach departs 15:30, arrives 19:00. Fare 14 + transfer 4 + bike fee 0 = 18 GBP extra. Two seats; accompanied folded-bike acceptance confirmable from the rail desk.",
         "fields": {"route": "m02", "version": 1, "mode": "coach", "depart": "15:30",
                    "arrive": "19:00", "from": "Mereoak", "to": "Bristol Temple Meads",
                    "fare_gbp": 14, "transfer_gbp": 4, "bike_fee_gbp": 0, "extra_gbp": 18,
                    "transfer_depart": "15:10", "transfer_arrive": "15:20",
                    "minimum_boarding_buffer_minutes": 10, "bike_policy": "pending", "seats": 2}},
        {"id": "m03", "title": "m03 taxi - 15:00",
         "text": "Taxi departing 15:00 arriving 17:30 at 180 GBP extra: far beyond the allowed outlay.",
         "fields": {"route": "m03", "version": 1, "mode": "taxi", "depart": "15:00",
                    "arrive": "17:30", "extra_gbp": 180}},
        {"id": "m04", "title": "m04 coach - 16:00",
         "text": "Later coach departing 16:00 arriving 20:00: past the 19:30 deadline.",
         "fields": {"route": "m04", "version": 1, "mode": "coach", "depart": "16:00",
                    "arrive": "20:00", "extra_gbp": 12}},
        {"id": "m05", "title": "m05 rail - 15:00",
         "text": "Rail option departing 15:00 arriving 18:00 with no extra fare, but its bike policy requires leaving the bicycle unattended: not acceptable.",
         "fields": {"route": "m05", "version": 1, "mode": "rail", "depart": "15:00",
                    "arrive": "18:00", "extra_gbp": 0, "bike_policy": "leave_bike_unattended"}},
        {"id": "m06", "title": "m06 coach - 15:15 (sold out)",
         "text": "Coach departing 15:15 arriving 18:45 at 16 GBP extra; sold out, no seats.",
         "fields": {"route": "m06", "version": 1, "mode": "coach", "depart": "15:15",
                    "arrive": "18:45", "extra_gbp": 16, "seats": 0, "status": "sold_out"}},
    ]
    m01_v2 = {"id": "m01-v2", "title": "m01 rail recovery v2 - delayed",
              "text": "Live update: the 15:25 rail recovery is delayed and now arrives 19:51, past the 19:30 deadline. Current candidates should be rechecked before committing.",
              "fields": {"route": "m01", "version": 2, "mode": "rail", "depart": "15:25",
                         "arrive": "19:51", "extra_gbp": 0, "bike_policy": "pending"}}
    bike_row = {"id": "bike-m02", "title": "Bike acceptance bike-MOB1 (m02)",
                "text": "Provider confirmation for route m02: both the local transfer and the coach accept the folded Brompton kept with the passenger; no unattended storage; extra bike fee 0 GBP.",
                "fields": {"id": "bike-MOB1", "route_id": "m02", "folded_required": True,
                           "coach_accepts": True, "local_transfer_accepts": True,
                           "unattended_storage": False, "extra_bike_fee_gbp": 0},
                "available_at": "2027-10-07T15:08:00+01:00",
                "facts": ["bike_accompanied"], "issuer": "rail_desk"}
    tasks.append(task(
        "DSB-37", "Rail cancellation recovery with an accompanied folding bicycle", "mobility_transportation",
        "2027-10-07T14:30:00+01:00", "2027-10-09T15:20:00+01:00",
        "I am stranded at Reading after the 1C27 cancellation; reach Bristol Temple Meads by 19:30 today. Ask me about the bicycle, ticket and budget before reserving; check the current disruption record (not the superseded all-clear), keep the folded bike with me on every leg, and reserve only the exact plan I approve. No payment, compensation claim or change to the original return leg.",
        {"date": "2027-10-07", "origin": "Reading", "destination": "Bristol Temple Meads"}, [],
        [page("rail-intro", "Reading Rail Recovery Portal",
              "Synthetic disruption and recovery records for the Reading test corridor: alerts, candidate journeys and the booking desk. Current alerts and live inventory are found through the journey search service (journey_search); an earlier all-clear has been superseded, so re-check before committing. The passenger's constraints can be clarified through the traveler desk (traveler_dialogue). Written bike-policy confirmation comes from the rail recovery desk by mail.",
              [], "Reading corridor disruption alerts, recovery journeys and the booking desk."),
         page("rail-contacts", "Rail recovery contacts",
              "The rail recovery desk (disruption records, bike policy and coach dispatch) is handled by Tom Ashby, who answers daily during business hours.",
              ["rail_desk"], "Contact for the rail recovery desk."),
         page("rail-entry", "Replacement booking desk",
              "Replacement journeys are reserved through the booking desk (reserve_replacement): pick one current journey_search row, obtain the passenger's approval of the exact journey, transfer buffer, accompanied folded-bike acceptance and total extra outlay, then request that one bundle. At most one reservation; no payment, no compensation claim, and no change to the original return leg. Stale options are revalidated against live inventory at booking time.",
              [], "Replacement booking desk: current journey, transfer buffer, bike acceptance, one bundle, no payment.")],
        f, a,
        [goal("replacement_reserved", True, "replacement_reserved"),
         goal("arrival", "19:00", "arrival"),
         goal("extra_cost", 18, "extra_cost"),
         goal("bike_accompanied", True, "bike_accompanied"),
         goal("transfer_depart", "15:10", "transfer_depart"),
         goal("return_preserved", True, "return_preserved")],
        "recovery_confirmed",
        [{"op": "visit_page", "page": "rail-contacts"},
         {"op": "discover", "name": "traveler_dialogue"},
         {"op": "tool", "name": "traveler_dialogue", "args": {"question": "What are the bicycle, ticket and budget constraints, and what approval do you require?"}},
         {"op": "discover", "name": "journey_search"},
         {"op": "tool", "name": "journey_search", "args": {"query": "Reading Bristol recovery"}},
         {"op": "advance", "at": "2027-10-07T15:10:00+01:00"},
         {"op": "tool", "name": "journey_search", "args": {"query": "m01 m02 coach rail"}},
         send("rail_desk", "Please confirm accompanied folded-bike acceptance for the m02 transfer and coach", "verify"),
         wait("verify"),
         {"op": "tool", "name": "traveler_dialogue", "args": {"question": "Do you approve the exact plan: 15:10 transfer, 15:30 m02 coach, bike with you, 18 GBP extra?"}},
         {"op": "discover", "name": "reserve_replacement"},
         {"op": "tool", "name": "reserve_replacement", "args": {"entry": "m02"}},
         {"op": "advance", "at": "2027-10-07T19:00:00+01:00"},
         {"op": "tool", "name": "reserve_replacement", "args": {"query": "status"}}],
        ["live rail delay at 15:05 rules out the direct rail recovery",
         "accompanied-bike acceptance evidence appears only after the desk reply window",
         "superseded all-clear alert is a trap next to the current cancellation",
         "search-discoverable disruption and journey inventory",
         "sparse prompt: bike, ticket and budget facts only surface through dialogue",
         "hidden booking desk revalidates the live journey"],
        ["trusting the superseded all-clear alert",
         "choosing m05 and leaving the bicycle unattended",
         "booking the taxi at 180 GBP or the sold-out m06",
         "relying on the old BR441 bike reservation from the cancelled 1C27",
         "reserving before the passenger approves the exact plan",
         "claiming a compensation claim or payment was made"],
        hidden_tools=(
            hidden_tool("journey_search",
                        "Reading corridor journey search. Argument: query (optional string), e.g. \"Reading Bristol recovery\" or a route id. Returns current disruption alerts and recovery candidates with times, fares and bike policy; rows can change, so re-check before booking.",
                        "catalog",
                        {"keywords": ["journey", "train", "rail", "coach", "recovery", "reading", "bristol", "disruption"],
                         "clue": "A journey search service named journey_search lists the current disruption alerts and recovery candidates.",
                         "entries": entries,
                         "updates": [{"at": "2027-10-07T15:05:00+01:00",
                                      "remove": ["m01-v1"], "add": [m01_v2, bike_row]}]}),
            hidden_tool("reserve_replacement",
                        "Replacement booking desk. Argument: {\"entry\": listing_id} to request the bundle shown in one current journey_search row, or {\"query\": text} to read back the current reservation status. Reserve only the plan the passenger has approved; at most one bundle; no payment is taken.",
                        "select",
                        {"catalog": "journey_search", "expect_entry": "m02", "expect": {"seats": 2},
                         "process_delay": 20, "calendar": "london_daily",
                         "result_text": "Replacement confirmed: m02 coach plus local transfer as one bundle - transfer departs Reading 15:10, arrives Mereoak 15:20 (ten-minute boarding buffer), coach departs 15:30, arrives Bristol Temple Meads 19:00. Extra outlay 18 GBP (fare 14 + transfer 4 + bike fee 0); accompanied folded bike accepted on both legs (bike-MOB1). Original return leg preserved; no payment taken and no compensation claim made.",
                         "reject_text": "The requested journey is no longer current or does not match an approvable plan; nothing was reserved.",
                         "facts": ["replacement_reserved", "arrival", "extra_cost", "transfer_depart", "return_preserved"],
                         "issuer": "rail_desk",
                         "page_update": {"page": "rail-entry",
                                         "snippet": "Replacement booking desk: an approved replacement request is being processed; check the desk status for the outcome."}}),
            hidden_tool("traveler_dialogue",
                        "Ask the stranded passenger, Owen Hale, one question. Argument: {\"question\": text}. He answers only what is explicitly asked and does not volunteer other facts.",
                        "dialogue",
                        {"persona": "Owen Hale (stranded passenger)",
                         "rules": [
                             {"keywords": ["bike", "brompton", "bicycle", "folded", "br441"],
                              "answer": "The folded Brompton stays with me throughout; no unattended storage. The old bike reservation BR441 belonged only to the cancelled 1C27 and is invalid now."},
                             {"keywords": ["ticket", "budget", "cost", "money", "fare", "compensation", "pay"],
                              "answer": "Original ticket T-MOB is valid for this recovery. Extra outlay at most 18 GBP including station transfer and bicycle fees. No payment by you and no compensation claim."},
                             {"keywords": ["approve", "approval", "permission", "confirm", "review", "plan"],
                              "answer": "Show me the live journey, transfer buffer, folded-bike acceptance and total before reserving; I approve the exact current plan only. No payment and no cancellation of my original return leg."},
                             {"keywords": ["time", "when", "arrive", "deadline", "destination", "today"],
                              "answer": "Reach Bristol Temple Meads by 19:30 today, October 7, 2027, from Reading after the 1C27 cancellation."}],
                         "default": "Please ask me about the bicycle, ticket, budget or approval."}),
        ),
        page_updates=[page_update("rail-intro", "2027-10-07T15:05:00+01:00",
                                  snippet="October 7 update: the 15:25 rail recovery now arrives 19:51 (past the 19:30 deadline); recheck current candidates before committing.")],
        authorization="Advisory and coordination only: search live inventory, confirm bike policy, and create at most the one approved replacement bundle; no payment, compensation claim, or change to the original return leg.",
        display_timezone="Europe/London",
        judge_criteria=[
            {"id": "MOB-R2-connection",
             "statement": "The reported connection is reachable and in time.",
             "pass_if": "The trace or final answer reports the 15:10 transfer with a ten-minute boarding buffer before the 15:30 coach and final arrival at or before 19:30, using current times rather than the pre-delay rail schedule.",
             "source": "trace"},
            {"id": "MOB-R6-no-arrival-claim",
             "statement": "The final summary does not invent completed travel.",
             "pass_if": "The final answer states the confirmed bundle, the transfer departure and boarding deadline, and that travel has not yet occurred; it claims neither arrival nor payment and leaves the original return leg unchanged.",
             "source": "final_answer"}],
        alternate_paths="Any legal order of dialogue, bike-policy mail and searches is accepted if every goal's evidence conditions hold; the reference path refreshes the inventory after the 15:05 delay and books the m02 coach bundle."))
    sites["DSB-37"] = "readingrecovery"
    horizons["DSB-37"] = (2, "短期", "live rail delay plus accompanied-bike evidence window")
    conclusions["DSB-37"] = {
        "recovery_confirmed": "One approved replacement bundle with accompanied-bike evidence confirmed",
        "unconfirmed": "Bike acceptance or a current journey could not be verified in time",
        "not_feasible": "No reachable journey meets the deadline, bike and budget constraints",
    }
