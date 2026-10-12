// The three tools the reservation agent can call. They are thin wrappers over
// the canned booking book in bistro.ts. Nothing here knows about tracing.
import { createTool } from "@voltagent/core";
import { z } from "zod";
import { availability, book, cancel, longDate } from "./bistro.ts";

export const checkAvailability = createTool({
  name: "check_availability",
  description:
    "Check which dinner slots have a free table for a party on a given date. " +
    "Optionally pass a preferred time to see the slots around it.",
  parameters: z.object({
    date: z.string().describe("Date as YYYY-MM-DD, e.g. 2026-11-13"),
    party_size: z.number().int().min(1).describe("Number of guests"),
    around_time: z.string().optional().describe("Preferred time as HH:MM (24h), e.g. 19:30"),
  }),
  execute: async ({ date, party_size, around_time }) => availability(date, party_size, around_time),
});

export const bookTable = createTool({
  name: "book_table",
  description:
    "Book a table. Only call this after check_availability showed the slot is free " +
    "and the guest clearly asked to book it. Returns the booking confirmation.",
  parameters: z.object({
    name: z.string().describe("Name the booking is under"),
    date: z.string().describe("Date as YYYY-MM-DD"),
    time: z.string().describe("Time as HH:MM (24h)"),
    party_size: z.number().int().min(1).describe("Number of guests"),
  }),
  execute: async ({ name, date, time, party_size }) => {
    const result = book(name, date, time, party_size);
    return "error" in result ? result : { ...result, weekday_date: longDate(result.date) };
  },
});

export const cancelBooking = createTool({
  name: "cancel_booking",
  description:
    "Cancel an existing booking. Needs the booking id (like ML-1050) and the name it is under.",
  parameters: z.object({
    booking_id: z.string().describe("The booking id, like ML-1050"),
    name: z.string().describe("Name the booking is under"),
  }),
  execute: async ({ booking_id, name }) => cancel(booking_id, name),
});
