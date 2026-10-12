// The loans desk's three tools, backed by the in-memory data in library.ts.
// Nothing here knows about tracing: Mastra wraps every execute() in a tool span.
import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { BOOKS, MAX_RENEWALS, RENEWAL_DAYS, findBook, findMember } from "./library.ts";

export const searchCatalog = createTool({
  id: "search_catalog",
  description:
    "Search the library catalog by title, author or genre keywords. Returns matching books with " +
    "book_id, copies available and how many patrons are waiting on a hold.",
  inputSchema: z.object({
    query: z.string().describe("Keywords from the title, author or genre"),
  }),
  execute: async ({ query }) => {
    const words = query.toLowerCase().split(/\W+/).filter((w) => w.length > 2);
    const matches = BOOKS.filter((b) => {
      const haystack = `${b.title} ${b.author} ${b.genre}`.toLowerCase();
      return words.some((w) => haystack.includes(w));
    });
    return { query, count: matches.length, results: matches };
  },
});

export const renewLoan = createTool({
  id: "renew_loan",
  description:
    `Renew one of a member's loans for ${RENEWAL_DAYS} more days. Refused if the member's card is ` +
    `not active, the loan was already renewed ${MAX_RENEWALS} times, the loan is overdue, or other ` +
    "patrons are waiting on a hold for that book.",
  inputSchema: z.object({
    member_id: z.string().describe("The member id, like M-2041"),
    loan_id: z.string().describe("The loan id, like L-8801"),
  }),
  execute: async ({ member_id, loan_id }) => {
    const member = findMember(member_id);
    if (!member) return { renewed: false, reason: "unknown_member", message: `No member ${member_id}.` };
    if (member.card_status !== "active")
      return { renewed: false, reason: "card_blocked", message: "The library card is not active." };
    const loan = member.loans.find((l) => l.loan_id.toLowerCase() === loan_id.trim().toLowerCase());
    if (!loan) return { renewed: false, reason: "unknown_loan", message: `${member.name} has no loan ${loan_id}.` };
    const book = findBook(loan.book_id)!;
    if (loan.due_in_days < 0)
      return { renewed: false, reason: "overdue", title: book.title, message: "Overdue loans cannot be renewed." };
    if (loan.renewals_used >= MAX_RENEWALS)
      return { renewed: false, reason: "renewal_limit", title: book.title, message: `Already renewed ${MAX_RENEWALS} times.` };
    if (book.holds_waiting > 0)
      return {
        renewed: false,
        reason: "hold_queue",
        title: book.title,
        holds_waiting: book.holds_waiting,
        message: "Other patrons are waiting for this book, so it cannot be renewed.",
      };
    loan.renewals_used += 1;
    loan.due_in_days += RENEWAL_DAYS;
    return { renewed: true, loan_id: loan.loan_id, title: book.title, new_due_in_days: loan.due_in_days, renewals_used: loan.renewals_used };
  },
});

export const placeHold = createTool({
  id: "place_hold",
  description:
    "Place a hold for a member on a book that is checked out. Returns the member's position in the " +
    "hold queue. Refused if the book has copies on the shelf (the member can just borrow it) or " +
    "the member already has it on loan.",
  inputSchema: z.object({
    member_id: z.string().describe("The member id, like M-2041"),
    book_id: z.string().describe("The book id from search_catalog, like BK-302"),
  }),
  execute: async ({ member_id, book_id }) => {
    const member = findMember(member_id);
    if (!member) return { placed: false, reason: "unknown_member", message: `No member ${member_id}.` };
    const book = findBook(book_id);
    if (!book) return { placed: false, reason: "unknown_book", message: `No book ${book_id}.` };
    if (member.loans.some((l) => l.book_id === book.book_id))
      return { placed: false, reason: "already_on_loan", title: book.title, message: "The member already has this book on loan." };
    if (book.copies_available > 0)
      return { placed: false, reason: "copy_available", title: book.title, copies_available: book.copies_available, message: "A copy is on the shelf, no hold needed." };
    book.holds_waiting += 1;
    return { placed: true, title: book.title, queue_position: book.holds_waiting, message: "Hold placed. The member gets an email when it is ready." };
  },
});
