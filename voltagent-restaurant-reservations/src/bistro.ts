// The bistro's in-memory "reservation system". Everything is canned so the demo
// needs no database: only the LLM call leaves your machine.
//
// Maison Lanterne is a fictional 14-table bistro. Tables come in three sizes,
// and the book is seeded with a few existing reservations so availability is
// not a foregone conclusion.

export type TableSize = 2 | 4 | 6;

type Table = { id: string; seats: TableSize };

export type Booking = {
  booking_id: string;
  name: string;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM, 24h
  party_size: number;
  table_id: string;
};

export const TODAY = "2026-11-09"; // a Monday; the system prompt tells the agent so
export const SLOTS = ["17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"];
export const OPEN_DATES = ["2026-11-12", "2026-11-13", "2026-11-14", "2026-11-15"]; // Thu-Sun

const TABLES: Table[] = [
  ...["T1", "T2", "T3", "T4", "T5", "T6"].map((id) => ({ id, seats: 2 as const })),
  ...["T7", "T8", "T9", "T10", "T11"].map((id) => ({ id, seats: 4 as const })),
  ...["T12", "T13", "T14"].map((id) => ({ id, seats: 6 as const })),
];

const bookings: Booking[] = [
  // Friday evening is nearly full for parties of four at 19:30.
  { booking_id: "ML-1042", name: "Tomas Reyes", date: "2026-11-13", time: "19:30", party_size: 4, table_id: "T7" },
  { booking_id: "ML-1043", name: "Priya Nair", date: "2026-11-13", time: "19:30", party_size: 3, table_id: "T8" },
  { booking_id: "ML-1044", name: "Jonas Aalto", date: "2026-11-13", time: "19:30", party_size: 4, table_id: "T9" },
  { booking_id: "ML-1045", name: "Chloe Martin", date: "2026-11-13", time: "19:30", party_size: 4, table_id: "T10" },
  { booking_id: "ML-1046", name: "Dev Patel", date: "2026-11-13", time: "19:30", party_size: 2, table_id: "T11" },
  // The two six-tops at 19:30 are taken too, so 19:30 has no table for four.
  { booking_id: "ML-1047", name: "Sofia Greco", date: "2026-11-13", time: "19:30", party_size: 6, table_id: "T12" },
  { booking_id: "ML-1048", name: "Kwame Mensah", date: "2026-11-13", time: "19:30", party_size: 5, table_id: "T13" },
  { booking_id: "ML-1049", name: "Lena Fischer", date: "2026-11-13", time: "19:30", party_size: 6, table_id: "T14" },
  // Saturday, one booking that a later request will cancel.
  { booking_id: "ML-1050", name: "Hugo Bernard", date: "2026-11-14", time: "20:00", party_size: 2, table_id: "T1" },
];

let nextBookingNumber = 1051;

function taken(date: string, time: string): Set<string> {
  return new Set(bookings.filter((b) => b.date === date && b.time === time).map((b) => b.table_id));
}

/** Smallest free table that fits the party, or undefined. */
function freeTable(date: string, time: string, partySize: number): Table | undefined {
  const busy = taken(date, time);
  return TABLES.filter((t) => t.seats >= partySize && !busy.has(t.id)).sort((a, b) => a.seats - b.seats)[0];
}

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** "Saturday 14 November 2026": spelled out so the model never has to do calendar math. */
export function longDate(date: string): string {
  const d = new Date(`${date}T12:00:00Z`);
  return `${WEEKDAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export type Availability =
  | { error: string }
  | { date: string; weekday_date: string; party_size: number; slots: { time: string; available: boolean }[] };

export function availability(date: string, partySize: number, aroundTime?: string): Availability {
  if (!OPEN_DATES.includes(date)) {
    return { error: `Maison Lanterne takes bookings Thursday to Sunday only (${OPEN_DATES.join(", ")}).` };
  }
  if (partySize < 1 || partySize > 6) {
    return { error: "We seat parties of 1 to 6 online. Larger groups should call the restaurant." };
  }
  let slots = SLOTS;
  if (aroundTime) {
    const i = SLOTS.indexOf(aroundTime);
    slots = i === -1 ? SLOTS : SLOTS.slice(Math.max(0, i - 2), i + 3);
  }
  return { date, weekday_date: longDate(date), party_size: partySize, slots: slots.map((time) => ({ time, available: !!freeTable(date, time, partySize) })) };
}

export function book(name: string, date: string, time: string, partySize: number): Booking | { error: string } {
  if (!OPEN_DATES.includes(date) || !SLOTS.includes(time)) {
    return { error: `No service at ${date} ${time}. Slots run ${SLOTS[0]}-${SLOTS[SLOTS.length - 1]}, Thursday to Sunday.` };
  }
  const table = freeTable(date, time, partySize);
  if (!table) return { error: `No table for ${partySize} at ${time} on ${date}.` };
  const booking: Booking = {
    booking_id: `ML-${nextBookingNumber++}`,
    name,
    date,
    time,
    party_size: partySize,
    table_id: table.id,
  };
  bookings.push(booking);
  return booking;
}

export function cancel(bookingId: string, name: string): { cancelled: Booking } | { error: string } {
  const i = bookings.findIndex((b) => b.booking_id === bookingId.toUpperCase().trim());
  if (i === -1) return { error: `No booking with id ${bookingId}.` };
  if (bookings[i].name.toLowerCase() !== name.toLowerCase().trim()) {
    return { error: `Booking ${bookingId} is not under the name ${name}.` };
  }
  const [removed] = bookings.splice(i, 1);
  return { cancelled: removed };
}
