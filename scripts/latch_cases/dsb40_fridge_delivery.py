"""DSB-40 <- LATCH case shopping-refrigerator-delivery-001 (fridge order with
verified access and a mid-episode delivery-slot change). Six noisy listings,
written unpack-at-door fit evidence, an approval window, and one approved
pay-on-delivery order."""

LATCH_CASE = "shopping-refrigerator-delivery-001"


def build(A, tasks, sites, horizons, conclusions):
    # ---- DSB-40 <- LATCH shopping-refrigerator-delivery-001 -----------------
    # One refrigerator order with verified installation access, complete price
    # and a delivery-slot change. The LATCH product.search becomes a hidden
    # kind="catalog" tool (product_search, discoverable via web_search
    # keywords) whose inventory carries the six noisy listings; the S-DELIVERY
    # event (June 8 12:00: the uncommitted COOL-17-A early route moves to
    # June 11, past the deadline) becomes a product_search catalog update plus
    # a page_update at the event's authored time. The LATCH
    # fulfillment.contact/status + S-FIT event become a mail workflow on the
    # delivery specialist (measured fit, unpack-at-door and recycling evidence
    # publish from June 8 09:00, encoded with accept_after). The LATCH
    # order.quote/plan.validate/order.create chain condenses into one hidden
    # kind="select" tool (order_create): only the current COOL-16-B listing at
    # 1181.60 USD all-in is acceptable, and acceptance issues the order
    # evidence. The LATCH user.dialogue becomes a hidden kind="dialogue" tool
    # (householder_dialogue): the sparse prompt's installation, access,
    # delivery and authorization facts never appear on any page, only by
    # asking. The case deadline (June 8 17:00) is 32h after start; DSB
    # validation requires a >= 2-day horizon, so the deadline moves to June 9
    # at 12:00 Chicago time - the delivery window end of the ordered unit.
    fact = A["fact"]; lookup = A["lookup"]; document = A["document"]
    acknowledge = A["acknowledge"]; reply = A["reply"]
    workflow = A["workflow"]; person = A["person"]
    page = A["page"]; goal = A["goal"]; task = A["task"]; send = A["send"]
    wait = A["wait"]; business = A["business"]; hidden_tool = A["hidden_tool"]
    page_update = A["page_update"]
    suggest = A["suggest"]; doc = A["doc"]; document_page = A["document_page"]

    f = {
        "ordered_sku": fact("COOL-16-B",
                            "The confirmed order is for COOL-16-B (16.5 cu ft, 31.5 in wide, Energy Star) from the test appliance store."),
        "order_total": fact(1181.6,
                            "The ordered total is 1181.60 USD all-in - item 1020.00, tax 81.60, delivery 50.00 and old-fridge recycling 30.00 - within the 1300 USD budget."),
        "delivery_window": fact("2027-06-09 10:00-12:00",
                                "The assigned confirmed delivery interval is 2027-06-09 10:00-12:00 Chicago time, inside the 08:00-18:00 access hours and ending well before the June 10 09:00 deadline."),
        "payment_terms": fact("pay_on_delivery",
                              "The order is pay-on-delivery only: the agent took no payment, opened no credit account, subscription or deposit."),
        "fit_verified": fact(True,
                             "The delivery specialist confirms in writing (fit-S206) that COOL-16-B's minimum opening (32.5 x 69 x 34 in) fits the measured 33 x 70 x 35 in opening, with a verified unpack-at-door procedure giving a 32 in route through the 33 in doorway."),
        "recycling_confirmed": fact(True,
                                    "Old-appliance recycling at the ground-floor address is included in the confirmed delivery service."),
        "elevator_reserved": fact("2027-06-09 09:30-10:00",
                                  "The building manager confirms in writing (lift booking L-0906) that the service elevator at 18 Example Court is reserved for the fridge delivery on 2027-06-09 09:30-10:00, ahead of the confirmed delivery interval."),
        # 甄别陷阱：开局即挂在门店页的街区比价单给出低于官方全含价的诱人总价，
        # 但整理方不具备本店报价签发权限，引用该证据会被评分拒绝；真值仍以
        # 库存台/订单台出具的书面确认为准。
        "total_ref": fact(1099.0,
                          "Neighborhood price comparison sheet, June 2027: COOL-16-B all-in 1099.00 USD with discounted delivery and waived recycling (compiled by the record holder).",
                          unauthorized_attestation=True),
    }
    a = [
        person("fulfillment_agent", "Test Appliance Cooperative delivery specialist·Morgan Hale",
               "measured dimensions, access verification and delivery slots", "us_central_daily",
               [workflow("Fit and delivery verification",
                         ["fit", "verify", "doorway", "unpack", "recycling", "access", "dimensions", "verification", "route", "opening"],
                         [],
                         [acknowledge(business(30)),
                          lookup(["fit_verified", "recycling_confirmed"], business(120),
                                 "check the measured opening, doorway route, unpack-at-door procedure and recycling"),
                          document(["fit_verified", "recycling_confirmed"], business(30)),
                          reply()],
                         accept_after="2027-06-08T09:00:00-05:00",
                         early_reply="Measured fit and delivery verification for this week's orders publishes from June 8 at 09:00 Chicago time; please resend your product and address details after that.")],
               "Confirms measured installation fit, the unpack-at-door route and recycling in writing; verified dimensions do not guarantee the current delivery slot still meets the deadline."),
        person("store_operations", "Test Appliance Cooperative inventory desk·Riley Carter",
               "listings, delivery slots and orders", "us_central_daily",
               [workflow("Listing and delivery slot status",
                         ["listing", "slot", "delivery", "stock", "offer", "price", "quote", "order"],
                         [],
                         [acknowledge(business(30)),
                          # 迷惑答复：库存台对楼栋通道不掌握，给出 hedge 猜测
                          # （可能找楼栋管理处，也可能配送队自理），需逐一验证。
                          suggest("I don't hold building-access arrangements, so I can only guess: the crew might handle freight entry themselves, or the building may run a service-elevator booking with its own manager - honestly not sure which; you'd want to check with the building side before the delivery window.",
                                  ["building_manager"], business(30)),
                          lookup(["order_total", "delivery_window"], business(60),
                                 "check the current listing, all-in total and delivery slot"),
                          document(["order_total", "delivery_window"], business(30)),
                          reply()], id="slot")],
               "Quotes current all-in totals and delivery slots; uncommitted delivery routes can change without notice, so slots are revalidated at order time. Building access and elevator bookings are not store records."),
        person("building_manager", "Example Court building manager·Jolene Fischer",
               "service-elevator bookings and freight access for 18 Example Court", "us_central_daily",
               [workflow("Service elevator booking",
                         ["elevator", "lift", "building", "freight", "court", "booking", "manager", "access"],
                         [],
                         [acknowledge(business(30)),
                          lookup(["elevator_reserved"], business(90),
                                 "check the service-elevator schedule and book the delivery slot"),
                          document(["elevator_reserved"], business(30)),
                          reply()])],
               "Books the building's service elevator for appliance deliveries in writing; the store does not manage building access, and delivery crews cannot enter without a confirmed booking."),
    ]
    # The inventory desk attests the order facts (SKU, total, window, terms)
    # but the primary issuance channel is the hidden order desk (order_create).
    a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"ordered_sku", "order_total", "delivery_window", "payment_terms"})
    entries = [
        {"id": "p201", "title": "COOL-17-A - 17 cu ft (headline 960 USD)",
         "text": "17 cu ft, Energy Star, 32 in wide, stock 2. Headline item price 960 USD; all-in 1121.80 USD (tax 76.80, delivery 60, recycling 25). Delivery 2027-06-09 10:00-12:00, pay on delivery; fit verification pending.",
         "fields": {"sku": "COOL-17-A", "capacity_cuft": 17, "width_in": 32, "energy_star": True,
                    "item_usd": 960, "tax_usd": 76.8, "delivery_usd": 60, "recycling_usd": 25, "total_usd": 1121.8,
                    "delivery_start": "2027-06-09T10:00:00-05:00", "delivery_end": "2027-06-09T12:00:00-05:00",
                    "payment_method": "pay_on_delivery", "offer_version": 1, "verification": "pending"}},
        {"id": "p202", "title": "CREDIT-17 - 17 cu ft (990 USD, store credit required)",
         "text": "17 cu ft, Energy Star, 32 in wide. The advertised 990 USD total requires opening a new store-credit account.",
         "fields": {"sku": "CREDIT-17", "capacity_cuft": 17, "width_in": 32, "energy_star": True,
                    "total_usd": 990, "payment_method": "new_store_credit", "requires_new_credit": True}},
        {"id": "p203", "title": "WIDE-20 - 20 cu ft (too wide)",
         "text": "20 cu ft, Energy Star, but 34 in wide - exceeds the 32.5 in limit.",
         "fields": {"sku": "WIDE-20", "capacity_cuft": 20, "width_in": 34, "energy_star": True,
                    "total_usd": 1200, "requires_new_credit": False}},
        {"id": "p204", "title": "BACKORDER-18 - 18 cu ft (backordered)",
         "text": "18 cu ft, Energy Star, 31 in wide, but out of stock; delivery 2027-06-14 misses the deadline.",
         "fields": {"sku": "BACKORDER-18", "capacity_cuft": 18, "width_in": 31, "energy_star": True,
                    "stock": 0, "total_usd": 1100, "delivery_start": "2027-06-14T10:00:00-05:00",
                    "requires_new_credit": False}},
        {"id": "p205", "title": "PREMIUM-17 - 17 cu ft (headline fits, all-in does not)",
         "text": "17 cu ft, Energy Star, 32 in wide, stock 1. Headline item price 1250 USD; all-in 1420.00 USD (tax 100, delivery 50, recycling 20).",
         "fields": {"sku": "PREMIUM-17", "capacity_cuft": 17, "width_in": 32, "energy_star": True,
                    "item_usd": 1250, "tax_usd": 100, "delivery_usd": 50, "recycling_usd": 20, "total_usd": 1420,
                    "requires_new_credit": False}},
        {"id": "p206", "title": "COOL-16-B - 16.5 cu ft (all-in 1181.60 USD)",
         "text": "16.5 cu ft, Energy Star, 31.5 in wide, stock 2. All-in 1181.60 USD (item 1020.00, tax 81.60, delivery 50, recycling 30). Delivery 2027-06-09 10:00-12:00, pay on delivery; fit verification pending.",
         "fields": {"sku": "COOL-16-B", "capacity_cuft": 16.5, "width_in": 31.5, "energy_star": True,
                    "item_usd": 1020, "tax_usd": 81.6, "delivery_usd": 50, "recycling_usd": 30, "total_usd": 1181.6,
                    "delivery_start": "2027-06-09T10:00:00-05:00", "delivery_end": "2027-06-09T12:00:00-05:00",
                    "payment_method": "pay_on_delivery", "offer_version": 1, "verification": "pending"}},
    ]
    p201_v2 = {"id": "p201", "title": "COOL-17-A - 17 cu ft (offer v2: delivery moved to June 11)",
               "text": "The uncommitted early delivery route for COOL-17-A is no longer available. Offer v2 delivery is 2027-06-11 14:00-16:00 - past the June 10 09:00 deadline. Earlier p201 quotes and approvals are invalid; COOL-16-B retains its separate June 9 slot.",
               "fields": {"sku": "COOL-17-A", "capacity_cuft": 17, "width_in": 32, "energy_star": True,
                          "total_usd": 1121.8, "delivery_start": "2027-06-11T14:00:00-05:00",
                          "delivery_end": "2027-06-11T16:00:00-05:00", "payment_method": "pay_on_delivery",
                          "offer_version": 2, "verification": "confirmed"}}
    tasks.append(task(
        "DSB-40", "Fridge replacement: verified access and a changed delivery slot", "shopping_commerce",
        "2027-06-07T09:00:00-05:00", "2027-06-09T12:00:00-05:00",
        "Our refrigerator failed. Find one with at least 16 cu ft, Energy Star, no wider than 32.5 in, at most 1300 USD all-in including tax, delivery and old-fridge recycling, delivered by 2027-06-10 09:00 Chicago time. Ask me about the space, access, address and ordering permission before ordering; the seller must verify unpack-at-door fit and recycling in writing, watch for delivery-slot changes, and make at most one approved order. Pay on delivery only - no new credit, subscription, deposit or agent payment.",
        {"need": "refrigerator replacement", "delivery_deadline": "2027-06-10", "min_capacity_cuft": 16,
         "max_width_in": 32.5, "budget_usd": 1300}, [],
        [document_page("store-intro", "Test Appliance Cooperative storefront",
              "Synthetic appliance listings for the test district; listing claims alone do not establish fit, eligibility or a confirmed delivery slot. Current listings are found through the store's product search service (product_search), and uncommitted delivery routes can change without notice, so re-check the live slot before ordering. Household space, access, address and approval facts can be clarified through the household desk (householder_dialogue). Measured fit, unpack-at-door and recycling confirmations come from the delivery specialist by mail; all-in totals come from the store's own desks in writing.",
              [], "Test Appliance Cooperative: refrigerator listings and household requirements desk.",
              [doc("price-comparison", "price-comparison.pdf",
                   "Neighborhood price comparison sheet, June 2027: COOL-16-B all-in 1099.00 USD with discounted delivery and waived recycling; COOL-17-A all-in 1040.00 USD. (compiled by the record holder)",
                   facts=["total_ref"], issuer="building_manager")]),
         page("store-contact", "Store contacts",
              "The delivery specialist (Morgan Hale) verifies measured installation fit, the doorway route, unpack-at-door handling and recycling; the inventory desk (Riley Carter) quotes current all-in totals and delivery slots; the building manager (Jolene Fischer) books the service elevator for 18 Example Court. All answer daily during business hours.",
              ["fulfillment_agent", "store_operations", "building_manager"], "Contacts for the delivery specialist, the inventory desk and the building manager."),
         page("store-entry", "Order desk",
              "Orders are placed through the store's order desk (order_create): pick one current product_search listing whose all-in total, payment terms and live delivery slot still satisfy the requirements, obtain the householder's approval of the exact SKU, fit evidence, delivery interval, recycling and full price (review available from June 8 at 13:00 Chicago time), then submit that one plan. At most one order; pay on delivery only - no new credit, subscription, deposit or agent payment. Stale offers are revalidated against live listings at order time.",
              [], "Order desk: one approved pay-on-delivery order, live slot only, no agent payment.")],
        f, a,
        [goal("ordered_sku", "COOL-16-B", "ordered_sku"),
         goal("order_total", 1181.6, "order_total"),
         goal("delivery_window", "2027-06-09 10:00-12:00", "delivery_window"),
         goal("payment_terms", "pay_on_delivery", "payment_terms"),
         goal("fit_verified", True, "fit_verified"),
         goal("recycling_confirmed", True, "recycling_confirmed"),
         goal("elevator_booked", "2027-06-09 09:30-10:00", "elevator_reserved")],
        "order_confirmed",
        [{"op": "visit_page", "page": "store-contact"},
         {"op": "discover", "name": "householder_dialogue"},
         {"op": "tool", "name": "householder_dialogue", "args": {"question": "What are the installation opening, doorway access, delivery details and ordering permission for the fridge replacement?"}},
         {"op": "discover", "name": "product_search"},
         {"op": "tool", "name": "product_search", "args": {"query": "refrigerator"}},
         send("fulfillment_agent", "Please verify measured fit, unpack-at-door handling and recycling for the candidate refrigerators at home-A", "fit_early"),
         wait("fit_early"),
         {"op": "advance", "at": "2027-06-08T09:30:00-05:00"},
         send("fulfillment_agent", "Please verify measured fit, unpack-at-door handling and recycling for the candidate refrigerators at home-A", "fit"),
         send("building_manager", "Please book the service elevator at 18 Example Court for a refrigerator delivery on June 9 between 10:00 and 12:00", "elevator"),
         wait("fit"),
         wait("elevator"),
         {"op": "advance", "at": "2027-06-08T15:00:00-05:00"},
         {"op": "tool", "name": "product_search", "args": {"query": "refrigerator"}},
         {"op": "discover", "name": "order_create"},
         {"op": "tool", "name": "order_create", "args": {"entry": "p206"}},
         {"op": "advance", "at": "2027-06-08T18:00:00-05:00"},
         {"op": "tool", "name": "order_create", "args": {"query": "order"}}],
        ["Mid-episode delivery-slot rewrite removes COOL-17-A's June 9 route",
         "written fit verification publishes from June 8 09:00",
         "approval window opens June 8 at 13:00",
         "side thread: written service-elevator booking from the building manager",
         "unauthorized price-comparison sheet undercuts the official all-in total",
         "inventory desk hedge guess about building access needs verification",
         "search-discoverable listing inventory",
         "hidden order desk revalidates the live listing and slot",
         "noisy listings (new credit, too wide, backordered, headline-vs-all-in price)",
         "sparse prompt: household facts only surface through dialogue"],
        ["ordering on the headline item price instead of the all-in total",
         "citing the neighborhood comparison sheet's 1099.00 USD instead of the store's written total",
         "reusing COOL-17-A's stale June 9 delivery promise after the slot change",
         "ordering before the householder approves the exact plan",
         "opening the new-credit 990 USD offer",
         "treating a dispatch estimate or fit verification as a confirmed slot",
         "skipping the service-elevator booking and assuming the crew handles building access",
         "booking the too-wide, backordered or over-budget listings"],
        extra_tools=("check_schedule",),
        hidden_tools=(
            hidden_tool("product_search",
                        "Test Appliance Cooperative product search. Argument: query (optional string), e.g. \"refrigerator\" or a SKU. Returns the current listings with capacity, width, line-item prices, all-in totals and delivery windows; uncommitted delivery routes can change, so re-check the live slot before ordering.",
                        "catalog",
                        {"keywords": ["fridge", "refrigerator", "appliance", "freezer", "kitchen", "shopping", "delivery"],
                         "clue": "A store search service named product_search lists the current refrigerator offers.",
                         "entries": entries,
                         "updates": [{"at": "2027-06-08T12:00:00-05:00",
                                      "remove": ["p201"], "add": [p201_v2]}]}),
            hidden_tool("order_create",
                        "Test Appliance Cooperative order desk. Argument: {\"entry\": listing_id} to order the plan shown in one current product_search row, or {\"query\": text} to read back the current order status. Order only the plan the householder has approved; at most one order; pay on delivery only - the desk takes no payment and opens no credit.",
                        "select",
                        {"catalog": "product_search", "expect_entry": "p206",
                         "expect": {"total_usd": 1181.6, "payment_method": "pay_on_delivery"},
                         "process_delay": 120, "calendar": "us_central_daily",
                         "result_text": "Order confirmed: COOL-16-B (16.5 cu ft, Energy Star, 31.5 in wide) from the test appliance store for Angela Davis at home-A, 18 Example Court - all-in 1181.60 USD (item 1020.00, tax 81.60, delivery 50.00, recycling 30.00), assigned delivery 2027-06-09 10:00-12:00 Chicago time with verified unpack-at-door fit (fit-S206) and old-fridge recycling included. Pay on delivery by the customer; no payment taken, no credit opened, and delivery has not occurred.",
                         "reject_text": "The submitted listing is not a current approvable plan (the listing is ineligible, stale, or its delivery slot no longer meets the deadline); the request was returned and nothing was ordered.",
                         "facts": ["ordered_sku", "order_total", "delivery_window", "payment_terms"], "issuer": "store_operations",
                         "page_update": {"page": "store-entry",
                                         "snippet": "Order desk: an approved order request is being processed; check the desk status for the outcome."}}),
            hidden_tool("householder_dialogue",
                        "Ask the householder, Angela Davis, one question. Argument: {\"question\": text}. She answers only what is explicitly asked and does not volunteer other facts.",
                        "dialogue",
                        {"persona": "Angela Davis (householder). Practical and unhurried: she answers exactly what is asked, gives her measurements and access facts precisely, and reviews an exact order plan only once her June 8 13:00 window opens.",
                         "dialogue_mode": "llm",
                         "rules": [
                             {"keywords": ["request", "need", "size", "capacity", "cuft", "width", "energy", "budget", "deadline", "when"],
                              "answer": "At least 16 cubic feet, Energy Star, no wider than 32.5 inches, at most 1300 USD all-in including tax, delivery and old-fridge recycling, with delivery completed by June 10, 2027, 09:00 Chicago time."},
                             {"keywords": ["installation", "opening", "space", "measure", "fit"],
                              "answer": "The installation opening is 33 in wide, 70 in high, 35 in deep."},
                             {"keywords": ["access", "doorway", "stairs", "unpack", "route"],
                              "answer": "The narrowest doorway is 33 in and there are no stairs. Unpacking at the door is allowed if the provider confirms the procedure in writing."},
                             {"keywords": ["address", "delivery", "recipient", "zone", "hours", "recycling", "recycle"],
                              "answer": "Deliver to Angela Davis at home-A, 18 Example Court, Test City, zone-A; I am available 08:00-18:00 daily, and the old fridge should be recycled."},
                             {"keywords": ["approve", "approval", "permission", "confirm", "review", "authorize", "pay", "payment", "credit"],
                              "answer": "Use pay-on-delivery; I will handle payment myself. No new credit account, subscription or deposit. I can review from June 8 at 13:00 Chicago time - show the exact SKU, fit evidence, delivery interval, recycling and full price, and order only after I approve."},
                         ],
                         "default": "Please ask me about the requirements, the space, the access, the delivery details or the ordering permission."}),
        ),
        page_updates=[page_update("store-intro", "2027-06-08T12:00:00-05:00",
                                  text="Test Appliance Cooperative storefront (June 8 update): the uncommitted early delivery route for COOL-17-A is no longer available - its offer v2 delivery window is June 11 14:00-16:00, past the June 10 09:00 deadline, and earlier p201 quotes and approvals are invalid. COOL-16-B retains its separate June 9 10:00-12:00 slot. Listings are found through product_search; re-check the live slot before ordering. Household facts come from the household desk (householder_dialogue); written fit and recycling confirmations come from the delivery specialist by mail.",
                                  snippet="June 8 update: COOL-17-A delivery moved to June 11; COOL-16-B keeps its June 9 slot.")],
        authorization="Advisory and coordination only: search listings, contact the store, gather written fit verification, and place at most the one pay-on-delivery order the householder has approved; no payment, new credit account, subscription, deposit or other binding commitment.",
        display_timezone="America/Chicago",
        judge_criteria=[
            {"id": "S-R1-fit-verified",
             "statement": "The written fit and recycling verification is carried into the summary.",
             "pass_if": "The summary carries the fit verification's key elements: fit-S206 confirming COOL-16-B's minimum opening fits the measured 33 x 70 x 35 in opening with the verified unpack-at-door route, and old-fridge recycling included in the delivery service.",
             "source": "final_answer"},
            {"id": "S-R2-order-receipt",
             "statement": "The order receipt's key elements reach the summary.",
             "pass_if": "The summary carries the order receipt's key elements: COOL-16-B for Angela Davis at home-A, all-in 1181.60 USD (item 1020.00, tax 81.60, delivery 50.00, recycling 30.00) within the 1300 USD budget, assigned delivery 2027-06-09 10:00-12:00 Chicago time, pay on delivery.",
             "source": "final_answer"},
            {"id": "S-R3-elevator-booking",
             "statement": "The service-elevator booking receipt's key elements reach the summary.",
             "pass_if": "The summary carries the building manager's booking confirmation's key elements: lift booking L-0906 reserving the service elevator at 18 Example Court for 2027-06-09 09:30-10:00, ahead of the 10:00-12:00 delivery window.",
             "source": "final_answer"},
            {"id": "S-R6-accurate-comparison",
             "statement": "The final explanation is accurate about tradeoffs and remaining work.",
             "pass_if": "The final answer reports the exact product, full all-in price and confirmed delivery interval, explains the rejection of the new-credit, late-delivery, backordered or over-budget offers (including the headline-vs-all-in price trap), and states that payment and delivery remain pending rather than completed.",
             "source": "final_answer"}],
        stages=[
            {"id": "householder-consulted", "kind": "tool_call", "target": "householder_dialogue",
             "hint": "The household facts are known: 33 x 70 x 35 in opening, 33 in doorway with no stairs, home-A delivery 08:00-18:00, recycling wanted, pay-on-delivery only and review from June 8 13:00."},
            {"id": "fit-verified", "kind": "fact_registered", "target": "fit_verified",
             "hint": "The delivery specialist's written verification is in: measured fit, unpack-at-door route and recycling confirmed in writing. Live slots can still change, so re-check before ordering."},
            {"id": "order-placed", "kind": "selection_processed", "target": "order_create",
             "hint": "The one approved pay-on-delivery order has been placed against the live listing and slot; the confirmation is read back through the order desk, never pushed."},
            {"id": "elevator-booked", "kind": "fact_registered", "target": "elevator_reserved",
             "hint": "The building manager confirms in writing: lift booking L-0906, service elevator reserved 2027-06-09 09:30-10:00 for the refrigerator delivery."}],
        alternate_paths="Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; ordering COOL-17-A was legal only before the June 8 12:00 slot change, but the scored answer keys follow the COOL-16-B plan."))
    sites["DSB-40"] = "fridgedelivery"
    horizons["DSB-40"] = (2, "Short term", "mid-episode delivery-slot rewrite plus approval window")
    conclusions["DSB-40"] = {
        "order_confirmed": "One approved pay-on-delivery order with verified fit and a deadline-meeting slot",
        "unconfirmed": "Fit, slot or approval could not be verified in time",
        "not_feasible": "No current listing satisfies the hard constraints",
    }
