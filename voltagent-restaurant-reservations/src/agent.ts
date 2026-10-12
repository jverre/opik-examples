import { Agent } from "@voltagent/core";
import { TODAY, OPEN_DATES, longDate } from "./bistro.ts";
import { bookTable, cancelBooking, checkAvailability } from "./tools.ts";

export const reservationAgent = new Agent({
  name: "lanterne-reservations",
  // VoltAgent's model router resolves "openai/gpt-4o-mini" to the AI SDK's
  // OpenAI provider and reads OPENAI_API_KEY from the environment.
  model: "openai/gpt-4o-mini",
  instructions:
    "You are the reservation assistant for Maison Lanterne, a small bistro open Thursday to Sunday. " +
    `Today is Monday ${TODAY}. The dates open for booking are: ` +
    `${OPEN_DATES.map((d) => `${longDate(d)} = ${d}`).join("; ")}. Use those exact YYYY-MM-DD values in tool calls. ` +
    "Never guess availability: call check_availability first. " +
    "Only call book_table when the guest clearly asked to book a slot that check_availability showed as free, " +
    "and only call cancel_booking when they give a booking id and the name on it. " +
    "If their slot is full, offer the nearest free slots. Confirm booking ids back to the guest. " +
    "Be warm and brief: 2-3 sentences.",
  tools: [checkAvailability, bookTable, cancelBooking],
});
