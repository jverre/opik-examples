// The art brief lives in the Opik prompt library. These are the two template
// versions the demo registers on a fresh workspace; after that the library is
// the source of truth and this file is just a readable changelog.

// Prefixed with the folder name so it is easy to find (and safe to delete) in a shared workspace.
export const PROMPT_NAME = "openai-image-boardgame-cards-art-brief";

// v1: what a designer types on day one. Describe the card, hope for the best.
// Saying "card" is the trap: image models answer with a whole mocked-up card.
export const BRIEF_V1 = `Board game {{card_type}} card "{{card_name}}" from the cooperative game "{{game}}".
Subject: {{subject}}.
Mood: {{mood}}.`;

// v2: the same brief after the print proof came back. Image models love to
// draw their own card frame and invent lettering, which collides with the
// frame and title bar the layout tool adds later.
export const BRIEF_V2 = `Board game {{card_type}} card "{{card_name}}" from the cooperative game "{{game}}".
Subject: {{subject}}.
Mood: {{mood}}.

Art direction (follow all of it):
- Style: flat gouache, visible paper grain, soft rounded shapes, warm lantern-lit palette.
- Artwork only. Do NOT draw a card frame, border, banner, title bar or any mock-up of a card.
- Absolutely no text, letters, numbers, runes that look like letters, or logos anywhere.
- One clear focal subject, centered, with calm empty space in the top fifth of the image.`;

export const V2_CHANGE_DESCRIPTION =
  "Added art direction: flat gouache style, artwork only (no frame or banner), no text, centered subject with empty top fifth";

export const GAME = "Emberwick Hollow";

// Two fictional cards from the deck. Each one is generated with both brief versions.
export const CARDS = [
  {
    id: "lantern-fox",
    card_name: "Lantern Fox",
    card_type: "creature",
    subject: "a small fox carrying a glowing paper lantern on a stick through a mossy forest path",
    mood: "cozy, curious, dusk",
  },
  {
    id: "moss-bridge",
    card_name: "Moss Bridge",
    card_type: "location",
    subject: "an old stone footbridge covered in moss over a quiet stream, fireflies above the water",
    mood: "calm, mysterious, early night",
  },
];

export const BRAND_GAME = { game: GAME };
