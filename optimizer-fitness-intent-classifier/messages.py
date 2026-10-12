"""Labeled in-app messages for Stridewell, a fictional fitness-coaching app.

Thirty messages, five intents, six per intent. The split is fixed so the
README can talk about it: four per intent go to TRAIN (what the optimizer
sees and climbs against) and two per intent go to VALIDATION (never shown
to the optimizer, used only to check the winner afterwards).

House rules behind the labels. Several messages touch more than one intent,
and the baseline prompt knows none of these rules:
  - When a message touches several intents, the highest-priority one wins:
    injury_concern > billing > sync_issue > change_plan > log_workout.
  - Any pain, swelling, dizziness, numbness or "is this a fracture" worry is
    injury_concern, even when the user mainly wants to log a run or cancel.
  - A workout missing because a device or integration failed is sync_issue,
    even when the user asks you to log it by hand.
  - Charges, refunds, cancellations, downgrades and invoices are billing.
  - A plain "log this" or "fix my log" with nothing else is log_workout.
  - Moving, shrinking or rebuilding upcoming training is change_plan.
"""

INTENTS = ["log_workout", "change_plan", "injury_concern", "billing", "sync_issue"]

# (message, intent)
TRAIN: list[tuple[str, str]] = [
    # --- log_workout ---
    ("Just finished a 5k in 28:40 and felt strong. Can you log it for today?", "log_workout"),
    ("Add yesterday's leg day: squats 4x8 at 80kg, lunges 3x12, calf raises 3x15.", "log_workout"),
    ("I did Thursday's HIIT on Friday instead. Please mark Thursday as completed.", "log_workout"),
    ("I logged my ride as 40 km but it was 30. Can you fix it?", "log_workout"),
    # --- change_plan ---
    ("Can I move my long run from Sunday to Saturday? I have a wedding this weekend.", "change_plan"),
    ("Add my 5k from today, and also can you make next week's plan lighter?", "change_plan"),
    ("Skip the speed session this week and log Tuesday's tempo run as done.", "change_plan"),
    ("I want to switch from fat loss to building muscle. Can you rebuild my program?", "change_plan"),
    # --- injury_concern ---
    ("Logged my 10k this morning but my hip has been clicking and painful since. Please add the run.", "injury_concern"),
    ("Cancel my subscription, I haven't been able to train since I tore my calf.", "injury_concern"),
    ("Make my plan easier, I've been getting dizzy on hard days.", "injury_concern"),
    ("I think I rolled my ankle in today's intervals and it's swelling. What do I do about tomorrow's session?", "injury_concern"),
    # --- billing ---
    ("Charged twice for Plus and the watch sync is also broken. Fix the charge first.", "billing"),
    ("Can you refund last month? I couldn't use the app, my watch wouldn't sync.", "billing"),
    ("I want to downgrade my plan because my watch data never syncs anyway.", "billing"),
    ("Please cancel my plan before it renews on the 3rd.", "billing"),
    # --- sync_issue ---
    ("My Garmin run never synced, please move Saturday's long run to Sunday.", "sync_issue"),
    ("Done with today's session: 3x10 squats. Also my Strava link is broken.", "sync_issue"),
    ("My run is on my watch but never appeared in Stridewell. Can you add it to my log for me?", "sync_issue"),
    ("Steps from my phone are double counted since I connected Strava.", "sync_issue"),
]

VALIDATION: list[tuple[str, str]] = [
    ("Did a 20 minute yoga flow before work, mark it done.", "log_workout"),
    ("Bench press 5x5 at 60kg today plus 10 minutes of core. Please add it to my history.", "log_workout"),
    ("Swap Thursday's HIIT for something low impact, the neighbors complain, and log my Wednesday swim.", "change_plan"),
    ("I'm training for a half marathon in 10 weeks. Can you build me a plan?", "change_plan"),
    ("Please log my 30 minute walk and tell me if the soreness in my shin is a stress fracture.", "injury_concern"),
    ("I was charged this month but I'm out with a back injury. Can I pause my plan?", "injury_concern"),
    ("Just add today's run, it was 8k. The charge on my card from yesterday looks off too.", "billing"),
    ("I need an invoice with our company's VAT number. My Garmin isn't syncing either.", "billing"),
    ("Heart rate data from my chest strap is missing from this morning's ride.", "sync_issue"),
    ("My bike computer shows the ride but Stridewell doesn't, can you just log it manually?", "sync_issue"),
]
