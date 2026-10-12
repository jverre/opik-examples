"""Five fictional voicemails left at the (made-up) Willow Bend Animal Clinic.

Everything here is synthetic: the callers, the pets, the phone numbers (all in
the 555-01xx fiction range). Each voicemail is one caller, spoken by one OpenAI
TTS voice, and is written the way people actually leave messages: rambling a
little, burying the important part, correcting themselves.

Two are deliberately tricky for a triage note:
  - rabbit-not-eating: a calm, polite caller describing a genuine emergency.
  - refill-number-correction: the caller corrects their own callback number.
"""

VOICEMAILS = [
    {
        "id": "chocolate-beagle",
        "caller": "Marcus Ellery",
        "voice": "onyx",
        "script": (
            "Hi, this is Marcus Ellery. Um, my beagle Biscuit just got into a "
            "whole bar of dark chocolate, the baking kind, I think about "
            "twenty minutes ago. He's panting a lot and kind of restless. I "
            "don't know if I should make him throw up or what. Please call me "
            "right away, my number is 555, 0142."
        ),
    },
    {
        "id": "cat-vaccines",
        "caller": "Priya Nair",
        "voice": "nova",
        "script": (
            "Hello, this is Priya Nair. I'm calling about my cat Mochi. Her "
            "annual vaccines are due next month and I'd like to book her in. "
            "Weekday afternoons work best for me, nothing urgent at all, she's "
            "doing great. You can reach me at 555, 0177. Thanks so much, bye."
        ),
    },
    {
        "id": "limping-labrador",
        "caller": "Tom Okafor",
        "voice": "echo",
        "script": (
            "Hey, it's Tom Okafor. My yellow Labrador, Juno, has been limping "
            "on her back left leg since yesterday afternoon. She's still "
            "eating and she still wants to play, but she won't put much weight "
            "on it. I'd like to get her seen this week if you can. Call me "
            "back on 555, 0119."
        ),
    },
    {
        "id": "rabbit-not-eating",
        "caller": "Dolores Whitcombe",
        "voice": "shimmer",
        "script": (
            "Oh, hello dear, this is Dolores Whitcombe, no rush at all, "
            "whenever you get a chance. It's my rabbit, Clementine. She hasn't "
            "eaten a single thing since last night, not even her favorite "
            "parsley, and she's very quiet and sitting hunched in the corner, "
            "and her tummy feels hard. I'm sure it's nothing. My number is "
            "555, 0163. Thank you, sweetheart."
        ),
    },
    {
        "id": "refill-number-correction",
        "caller": "Sam Reyes",
        "voice": "alloy",
        "script": (
            "Hi, Sam Reyes here. My dog Pepper is on the arthritis tablets, "
            "the daily ones, and I'm down to about five days' worth. Could "
            "someone call in a refill? My number is 555, 0131. Actually, "
            "sorry, that's 555, 0138. Zero one three eight. Thanks."
        ),
    },
]
