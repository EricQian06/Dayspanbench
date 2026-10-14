"""DSB-25 <- LATCH case cross-shopping-finance-installment-gate-001 (fridge
order gated on a live existing-card installment plan). Six noisy appliance
listings, a mid-episode promo expiry that rewrites the financing offer, and
one approved order that consumes the still-current installment plan."""

LATCH_CASE = "cross-shopping-finance-installment-gate-001"


def build(A, tasks, sites, horizons, conclusions):
    # ---- DSB-25 <- LATCH cross-shopping-finance-installment-gate-001 ---------
    # One refrigerator order bound to verified current financing. The LATCH
    # appliance.search and finance.read become hidden kind="catalog" tools
    # (appliance_search, finance_read, discoverable via web_search keywords).
    # The XSF-PROMO event (June 8 09:00: terms-A v1 expires, v2 adds a 120 USD
    # fee, 440 USD payments, 1320 total) becomes a finance_read catalog update
    # plus an appliance_search update (sf-A financed total rises to 1320) plus
    # a page_update, all at the event's authored time. The LATCH
    # fulfillment.verify + XSF-FIT event become a mail workflow on the
    # fulfillment desk (written fit/recycling/delivery confirmation). The LATCH
    # purchase.validate/installment.reserve/order.create chain condenses into
    # one hidden kind="select" tool (order_create): only the still-current
    # sf-B listing at 1140 USD is acceptable, and acceptance issues the order
    # and installment evidence. The LATCH user.dialogue becomes a hidden
    # kind="dialogue" tool (household_dialogue): the sparse prompt's fit, cash
    # and authorization facts never appear on any page, only by asking. The
    # case deadline (June 8 17:00) is 32h after start; DSB validation requires
    # a >= 2-day horizon, so the deadline moves to June 9 at 12:00 Chicago
    # time - the delivery window end of the ordered refrigerator.
    fact = A["fact"]; lookup = A["lookup"]; document = A["document"]
    acknowledge = A["acknowledge"]; reply = A["reply"]
    workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; hidden_tool = A["hidden_tool"]
    page_update = A["page_update"]

    f = {
        "ordered_sku": fact("sf-B",
                            "The confirmed order is for sf-B (16.5 cu ft, 31.5 in wide) from the test appliance store."),
        "order_total": fact(1140.0,
                            "The ordered plan totals 1140.00 USD all-in on the existing card, within the 1300 USD budget."),
        "installment_amount": fact(380.0,
                                   "The linked existing-card installment plan charges three zero-interest payments of 380.00 USD, each within the 400 USD residual cash after protected obligations."),
        "delivery_date": fact("2027-06-09",
                              "The ordered refrigerator is scheduled for delivery on 2027-06-09, before the June 10 deadline."),
        "fit_verified": fact(True,
                             "The fulfillment desk confirms in writing that sf-B fits the 33 in installation opening and 33 in ground-floor doorway with a verified unpack-at-door procedure."),
        "recycling_confirmed": fact(True,
                                    "Old-unit removal and recycling are included in the confirmed delivery service for the ordered refrigerator."),
    }
    a = [
        person("fulfillment_desk", "Test Appliance Cooperative fulfillment desk·Sam Rivers",
               "measured fit, doorway route and delivery verification", "us_central_daily",
               [workflow("Fit and delivery verification",
                         ["fit", "verify", "fitting", "doorway", "opening", "unpack", "recycling", "route", "access", "dimensions", "verification"],
                         [],
                         [acknowledge(business(30)),
                          lookup(["fit_verified", "recycling_confirmed", "delivery_date"], business(180),
                                 "check the installation opening, doorway route, unpack-at-door procedure and recycling"),
                          document(["fit_verified", "recycling_confirmed", "delivery_date"], business(30)),
                          reply()])],
               "Confirms measured installation fit, unpack-at-door handling, recycling and the current delivery date in writing; financing and orders go through the order desk."),
        person("store_desk", "Test Appliance Cooperative order desk·Dana Fields",
               "merchandise offers, financing terms and orders", "us_central_daily",
               [workflow("Current offer and financing quote",
                         ["offer", "quote", "price", "total", "financing", "installment", "terms", "payment", "order"],
                         [],
                         [lookup(["order_total", "installment_amount"], business(60),
                                 "check the current financed total and installment schedule"),
                          document(["order_total", "installment_amount"], business(30)),
                          reply()], id="quote")],
               "Quotes current financed totals and installment schedules; promo terms can expire and be replaced with fee-bearing versions, so quotes are revalidated at order time."),
    ]
    # The order desk attests the order facts (SKU, total, installment, delivery)
    # but the primary issuance channel is the hidden order desk (order_create).
    a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"ordered_sku", "order_total", "installment_amount", "delivery_date"})
    entries = [
        {"id": "sf-A", "title": "sf-A - 17 cu ft refrigerator (financed total 1200 USD)",
         "text": "17 cu ft, 32 in wide, delivery 2027-06-09. Existing-card zero-interest installments at 1200 USD total through offer terms-A v1.",
         "fields": {"sku": "sf-A", "capacity_cuft": 17, "width_in": 32, "total_usd": 1200,
                    "delivery": "2027-06-09", "stock": 2, "financing": "terms-A", "requires_new_credit": False}},
        {"id": "sf-B", "title": "sf-B - 16.5 cu ft refrigerator (financed total 1140 USD)",
         "text": "16.5 cu ft, 31.5 in wide, delivery 2027-06-09. Existing-card zero-interest installments at 1140 USD total through offer terms-B v1.",
         "fields": {"sku": "sf-B", "capacity_cuft": 16.5, "width_in": 31.5, "total_usd": 1140,
                    "delivery": "2027-06-09", "stock": 2, "financing": "terms-B", "requires_new_credit": False}},
        {"id": "sf-C", "title": "sf-C - 17 cu ft refrigerator (990 USD, new credit required)",
         "text": "17 cu ft, 32 in wide, delivery 2027-06-09. The 990 USD price requires opening a new credit account.",
         "fields": {"sku": "sf-C", "capacity_cuft": 17, "width_in": 32, "total_usd": 990,
                    "delivery": "2027-06-09", "requires_new_credit": True}},
        {"id": "sf-D", "title": "sf-D - 20 cu ft refrigerator (too wide)",
         "text": "20 cu ft but 34 in wide, delivery 2027-06-09; exceeds the 32.5 in width limit.",
         "fields": {"sku": "sf-D", "capacity_cuft": 20, "width_in": 34, "total_usd": 1200,
                    "delivery": "2027-06-09", "requires_new_credit": False}},
        {"id": "sf-E", "title": "sf-E - 17 cu ft refrigerator (delivery 2027-06-14)",
         "text": "17 cu ft, 32 in wide, but delivery 2027-06-14 misses the June 10 deadline.",
         "fields": {"sku": "sf-E", "capacity_cuft": 17, "width_in": 32, "total_usd": 1100,
                    "delivery": "2027-06-14", "requires_new_credit": False}},
        {"id": "sf-F", "title": "sf-F - 17 cu ft refrigerator (1420 USD)",
         "text": "17 cu ft, 32 in wide, delivery 2027-06-09, but the 1420 USD total exceeds the 1300 USD budget.",
         "fields": {"sku": "sf-F", "capacity_cuft": 17, "width_in": 32, "total_usd": 1420,
                    "delivery": "2027-06-09", "requires_new_credit": False}},
    ]
    sf_a_v2 = {"id": "sf-A", "title": "sf-A - 17 cu ft refrigerator (offer v2: financed total 1320 USD)",
               "text": "The zero-interest promo on sf-A expired on June 8. Offer terms-A v2 adds a 120 USD fee: 440 USD x 3 payments, 1320 USD total - above the 1300 USD budget and the 400 USD per-date residual cash.",
               "fields": {"sku": "sf-A", "capacity_cuft": 17, "width_in": 32, "total_usd": 1320,
                          "delivery": "2027-06-09", "financing": "terms-A v2", "offer_version": 2,
                          "fee_usd": 120, "requires_new_credit": False}}
    terms_a_v2 = {"id": "terms-A-v2", "title": "Offer terms-A v2 (sf-A, current)",
                  "text": "Promo expiry June 8 09:00: existing card, APR 0, but a 120 USD fee; payments 440 USD x 3, total 1320 USD. All version-1 validations, approvals and unused reservations are invalid.",
                  "fields": {"offer_id": "terms-A", "version": 2, "account": "card-existing", "apr": 0,
                             "fee_usd": 120, "payments": [440, 440, 440], "total_usd": 1320, "status": "current"}}
    finance_entries = [
        {"id": "terms-A-v1", "title": "Offer terms-A v1 (sf-A, expired June 8 09:00)",
         "text": "Existing card card-existing, APR 0, no fee, payments 400 USD on 2027-06-10, 2027-07-10, 2027-08-10, total 1200 USD. Status: superseded by version 2.",
         "fields": {"offer_id": "terms-A", "version": 1, "account": "card-existing", "apr": 0,
                    "fee_usd": 0, "payments": [400, 400, 400], "total_usd": 1200, "status": "expired"}},
        {"id": "terms-B", "title": "Offer terms-B (sf-B, current)",
         "text": "Existing card card-existing, APR 0, no fee, payments 380 USD on 2027-06-10, 2027-07-10, 2027-08-10, total 1140 USD.",
         "fields": {"offer_id": "terms-B", "version": 1, "account": "card-existing", "apr": 0,
                    "fee_usd": 0, "payments": [380, 380, 380], "total_usd": 1140, "status": "current"}},
        {"id": "cash-profile", "title": "Dated cash and credit profile",
         "text": "For each payment date (2027-06-10, 2027-07-10, 2027-08-10): 600 USD available cash and 200 USD protected obligations, leaving 400 USD residual. Protected obligations must stay untouched; card-existing has 1500 USD available credit.",
         "fields": {"payment_dates": ["2027-06-10", "2027-07-10", "2027-08-10"],
                    "cash_available": [600, 600, 600], "protected_obligations": [200, 200, 200],
                    "residual_cash": [400, 400, 400], "available_credit_usd": 1500}},
    ]
    tasks.append(task(
        "DSB-25", "Fridge replacement: installment-gated order with a promo expiry", "shopping_commerce",
        "2027-06-07T09:00:00-05:00", "2027-06-09T12:00:00-05:00",
        "Replace my refrigerator by 2027-06-10: at least 16 cu ft, width at most 32.5 in, total at most 1300 USD, delivered on time. Existing-card zero-interest installments only, no new credit. Ask me about the space, access, cash schedule and approval before reserving installments or ordering; seller must verify unpack-at-door handling and old-unit recycling, and watch for financing offer changes.",
        {"need": "refrigerator replacement", "delivery_deadline": "2027-06-10", "min_capacity_cuft": 16,
         "max_width_in": 32.5, "budget_usd": 1300}, [],
        [page("store-intro", "Test Appliance Cooperative storefront",
              "Synthetic appliance listings and financing offers for the test district; listing claims alone do not establish fit or current financing. Current merchandise is found through the store's appliance search service (appliance_search) and current installment terms through the financing reader (finance_read); offers can expire mid-week and be replaced with fee-bearing versions, so re-check terms before any commitment. Household space, cash and approval facts can be clarified through the household desk (household_dialogue). Measured fit, unpack-at-door and recycling confirmations come from the fulfillment desk by mail.",
              [], "Test Appliance Cooperative: refrigerator listings, installment offers and household requirements desk."),
         page("store-contact", "Store contacts",
              "The fulfillment desk (Sam Rivers) verifies measured installation fit, doorway route, unpack-at-door handling and recycling; the order desk (Dana Fields) quotes current financed totals and installment schedules. Both answer daily during business hours.",
              ["fulfillment_desk", "store_desk"], "Contacts for the fulfillment desk and the order desk."),
         page("store-entry", "Order and financing desk",
              "Orders are placed through the store's order desk (order_create): pick one current appliance_search listing whose financed total and payment schedule still satisfy the dated budget, obtain the household organizer's approval of the exact SKU, fees, payment dates and amounts, then submit that one plan. At most one order; no new credit account, interest, subscription, transfer from protected funds or payment outside the approved schedule. Stale offers and expired promo validations are revalidated against live terms at order time.",
              [], "Order desk: one approved plan, current financing only, no new credit.")],
        f, a,
        [goal("ordered_sku", "sf-B", "ordered_sku"),
         goal("order_total", 1140.0, "order_total"),
         goal("installment_amount", 380.0, "installment_amount"),
         goal("delivery_date", "2027-06-09", "delivery_date"),
         goal("fit_verified", True, "fit_verified"),
         goal("recycling_confirmed", True, "recycling_confirmed")],
        "order_financed",
        [{"op": "visit_page", "page": "store-contact"},
         {"op": "discover", "name": "household_dialogue"},
         {"op": "tool", "name": "household_dialogue", "args": {"question": "What are the installation opening, doorway, dated cash schedule and approval requirements for the fridge replacement?"}},
         {"op": "discover", "name": "appliance_search"},
         {"op": "tool", "name": "appliance_search", "args": {"query": "refrigerator"}},
         send("fulfillment_desk", "Please verify installation fit, unpack-at-door handling, recycling and the current delivery date for the candidate refrigerators", "verify_fit"),
         wait("verify_fit"),
         {"op": "discover", "name": "finance_read"},
         {"op": "advance", "at": "2027-06-08T10:00:00-05:00"},
         {"op": "tool", "name": "finance_read", "args": {"query": "terms"}},
         {"op": "tool", "name": "appliance_search", "args": {"query": "refrigerator"}},
         {"op": "discover", "name": "order_create"},
         {"op": "tool", "name": "order_create", "args": {"entry": "sf-B"}},
         {"op": "advance", "at": "2027-06-08T15:00:00-05:00"},
         {"op": "tool", "name": "order_create", "args": {"query": "order"}}],
        ["Mid-episode promo expiry rewrites the financing offer and the sf-A total",
         "written fit verification turnaround by mail",
         "search-discoverable merchandise and financing inventories",
         "hidden order desk revalidates the live financed plan",
         "noisy listings (new credit, too wide, late, over budget)",
         "sparse prompt: fit, cash and authorization facts only surface through dialogue"],
        ["ordering on a headline price instead of the financed total",
         "reusing the expired terms-A v1 validation or approval after June 8 09:00",
         "committing before the organizer approves the exact SKU, fees, dates and amounts",
         "opening the new-credit 990 USD offer",
         "counting protected obligations as available cash",
         "booking the too-wide, late-delivery or over-budget listings"],
        extra_tools=("check_schedule",),
        hidden_tools=(
            hidden_tool("appliance_search",
                        "Test Appliance Cooperative merchandise search. Argument: query (optional string), e.g. \"refrigerator\" or a SKU. Returns the current listings with capacity, width, totals and delivery; financed totals can change when promo offers expire, so re-check before ordering.",
                        "catalog",
                        {"keywords": ["fridge", "refrigerator", "appliance", "freezer", "kitchen", "shopping", "cuft"],
                         "clue": "A store search service named appliance_search lists the current refrigerator offers.",
                         "entries": entries,
                         "updates": [{"at": "2027-06-08T09:00:00-05:00",
                                      "remove": ["sf-A"], "add": [sf_a_v2]}]}),
            hidden_tool("finance_read",
                        "Financing reader for the existing card. Argument: query (optional string), e.g. \"terms\" or an offer id. Returns the current installment offers, payment dates, dated cash and protected obligations; expired versions are replaced, so affordability must be recomputed against the current version.",
                        "catalog",
                        {"keywords": ["finance", "installment", "credit", "card", "terms", "payments", "affordability", "budget", "cash"],
                         "clue": "A financing service named finance_read reports the current installment offers and dated cash profile.",
                         "entries": finance_entries,
                         "updates": [{"at": "2027-06-08T09:00:00-05:00",
                                      "remove": ["terms-A-v1"], "add": [terms_a_v2]}]}),
            hidden_tool("order_create",
                        "Test Appliance Cooperative order desk. Argument: {\"entry\": listing_id} to order the plan shown in one current appliance_search row, or {\"query\": text} to read back the current order status. Order only the plan the household organizer has approved; at most one order; the order consumes the current same-SKU installment plan - a price quote or expired promo is not a financing commitment.",
                        "select",
                        {"catalog": "appliance_search", "expect_entry": "sf-B", "expect": {"total_usd": 1140},
                         "process_delay": 120, "calendar": "us_central_daily",
                         "result_text": "Order confirmed: sf-B (16.5 cu ft, 31.5 in wide) delivered 2027-06-09, all-in 1140.00 USD on the existing card, consuming installment reservation finance-XSF1 - three zero-interest payments of 380.00 USD due 2027-06-10, 2027-07-10 and 2027-08-10, each within the 400 USD dated residual cash after protected obligations. No new credit, no fees, no payment executed; delivery and future payments remain pending.",
                         "reject_text": "The submitted plan is not a current approvable financed plan (the sf-A promo expired on June 8 with a 120 USD fee and 440 USD payments); the request was returned and nothing was ordered or reserved.",
                         "facts": ["ordered_sku", "order_total", "installment_amount", "delivery_date"], "issuer": "store_desk",
                         "page_update": {"page": "store-entry",
                                         "snippet": "Order desk: an approved order request is being processed; check the desk status for the outcome."}}),
            hidden_tool("household_dialogue",
                        "Ask the household organizer, Angela Davis, one question. Argument: {\"question\": text}. She answers only what is explicitly asked and does not volunteer other facts.",
                        "dialogue",
                        {"persona": "Angela Davis (household organizer), thrifty and protective of protected funds: she answers only what is asked, checks every fee and payment date, and approves only the exact SKU and schedule shown to her.",
                         "dialogue_mode": "llm",
                         "rules": [
                             {"keywords": ["request", "need", "size", "capacity", "cuft", "width", "budget", "deadline", "when"],
                              "answer": "Replace the fridge by June 10: at least 16 cu ft, width at most 32.5 in, total at most 1300 USD, existing-card zero-interest installments only - no new credit."},
                             {"keywords": ["fit", "opening", "space", "installation", "doorway", "access", "unpack", "recycling", "measure"],
                              "answer": "The installation opening is 33 in wide and the ground-floor doorway is 33 in. The seller must verify unpack-at-door handling and old-unit recycling in writing."},
                             {"keywords": ["cash", "money", "afford", "payment", "installment", "credit", "protected", "obligations"],
                              "answer": "For each of the next three installment dates I have 600 USD available cash and 200 USD protected obligations - keep those untouched, so each installment must stay within 400 USD. The existing card has 1500 USD available credit."},
                             {"keywords": ["approve", "approval", "permission", "confirm", "review", "authorize"],
                              "answer": "Show me the exact SKU, fees, payment dates and amounts for approval before reserving installments or ordering. No new account, no interest, no subscription, no transfer from protected funds, no extra payment outside the approved schedule."},
                         ],
                         "default": "Please ask me about the request, the space, the cash schedule or the approval arrangements."}),
        ),
        page_updates=[page_update("store-intro", "2027-06-08T09:00:00-05:00",
                                  text="Test Appliance Cooperative storefront (June 8 update): the zero-interest promo on sf-A expired at 09:00. Offer terms-A v2 adds a 120 USD fee - 440 USD x 3 payments, 1320 USD total - so sf-A no longer fits the 1300 USD budget or the 400 USD per-date residual cash; earlier validations, approvals and unused reservations on version 1 are invalid. sf-B's terms-B (380 USD x 3, 1140 USD total) remain current. Listings and terms are found through appliance_search and finance_read; re-check before ordering. Household facts come from the household desk (household_dialogue); written fit and recycling confirmations come from the fulfillment desk by mail.",
                                  snippet="June 8 update: sf-A promo expired - v2 totals 1320 USD with a 120 USD fee; sf-B terms remain current.")],
        authorization="Advisory and coordination only: search listings, contact the store, gather written fit verification, and place at most the one order the organizer has approved on the current existing-card installment plan; no new credit account, no payment, and no commitment outside the approved schedule.",
        display_timezone="America/Chicago",
        judge_criteria=[
            {"id": "XSF-R1-current-plan-only",
             "statement": "The order consumed a still-current financing plan.",
             "pass_if": "The trace shows the agent re-checked the financing after the June 8 promo expiry and ordered on the current sf-B terms-B plan (380 USD x 3, 1140 USD total), never on the expired terms-A v1 or its fee-bearing v2.",
             "source": "trace"},
            {"id": "XSF-R2-order-receipt",
             "statement": "The final summary carries the order receipt's key elements.",
             "pass_if": "The summary states the order of sf-B (16.5 cu ft, 31.5 in wide) delivered 2027-06-09, all-in 1140.00 USD on the existing card through reservation finance-XSF1 - three zero-interest payments of 380.00 USD due 2027-06-10, 2027-07-10 and 2027-08-10.",
             "source": "final_answer"},
            {"id": "XSF-R3-affordability-dated",
             "statement": "Each installment stayed within the dated residual cash.",
             "pass_if": "The trace or final answer shows each 380 USD payment fits the 400 USD residual cash per payment date after the 200 USD protected obligations stay untouched, with no new credit account opened.",
             "source": "trace"},
            {"id": "XSF-R4-fit-and-recycling",
             "statement": "Fit and recycling were verified in writing before the order.",
             "pass_if": "The summary reports the fulfillment desk's written confirmation that sf-B fits the 33 in installation opening and doorway with unpack-at-door handling, and that old-unit removal and recycling are included.",
             "source": "final_answer"},
            {"id": "XSF-R5-exact-side-effects",
             "statement": "Only exactly authorized side effects occurred.",
             "pass_if": "The trace shows the organizer's approval of the exact plan (SKU, fees, payment dates and amounts) preceding the installment reservation and order, one of each, with no new credit account, interest, subscription, transfer from protected funds or payment outside the approved schedule.",
             "source": "trace"},
            {"id": "XSF-R6-no-invented-performance",
             "statement": "Future performance is not invented.",
             "pass_if": "The final answer states the amounts and payment dates of the approved schedule and reports delivery and future payments as pending, without claiming any payment made or the appliance delivered.",
             "source": "final_answer"}],
        stages=[
            {"id": "household-constraints-known", "kind": "tool_call", "target": "household_dialogue",
             "hint": "The household organizer has been asked about the installation space, dated cash schedule and approval requirements; nothing has been ordered yet."},
            {"id": "fit-verified", "kind": "fact_registered", "target": "fit_verified",
             "hint": "The fulfillment desk's written fit, unpack-at-door and recycling confirmation has landed; the space claim now rests on provider measurements."},
            {"id": "financing-read", "kind": "tool_call", "target": "finance_read",
             "hint": "The current installment terms and dated cash profile are in the agent's hands; offers can expire mid-week, so affordability must be recomputed against the current version."},
            {"id": "order-confirmed", "kind": "selection_processed", "target": "order_create",
             "hint": "The one approved order on the current financed plan has been processed; the receipt is with the agent and delivery and payments remain pending."}],
        alternate_paths="Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the sf-A plan was legal only before the June 8 promo expiry, but the scored answer keys follow the current sf-B plan."))
    sites["DSB-25"] = "installmentgate"
    horizons["DSB-25"] = (2, "短期", "mid-episode promo expiry plus installment approval gate")
    conclusions["DSB-25"] = {
        "order_financed": "One approved order on a current existing-card installment plan within the dated budget",
        "unconfirmed": "Fit, financing or approval could not be verified in time",
        "not_feasible": "No current listing and financing combination satisfies the hard constraints",
    }
