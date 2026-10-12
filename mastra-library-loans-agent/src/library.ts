// The library's "systems": a catalog and a member/loan ledger loaded from the
// offline JSON files in data/. State lives in memory for one run, so a renewal
// or hold made by the agent is visible to later tool calls but never persisted.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const load = (name: string) =>
  JSON.parse(readFileSync(fileURLToPath(new URL(`../data/${name}`, import.meta.url)), "utf8"));

export interface Book {
  book_id: string;
  title: string;
  author: string;
  year: number;
  genre: string;
  copies_total: number;
  copies_available: number;
  holds_waiting: number;
}
export interface Loan {
  loan_id: string;
  book_id: string;
  due_in_days: number;
  renewals_used: number;
}
export interface Member {
  member_id: string;
  name: string;
  card_status: string;
  loans: Loan[];
}

export const LIBRARY_NAME: string = load("catalog.json").library;
export const BOOKS: Book[] = load("catalog.json").books;
export const MEMBERS: Member[] = load("members.json").members;

export const MAX_RENEWALS = 2;
export const RENEWAL_DAYS = 14;

export const findMember = (id: string) =>
  MEMBERS.find((m) => m.member_id.toLowerCase() === id.trim().toLowerCase());
export const findBook = (id: string) =>
  BOOKS.find((b) => b.book_id.toLowerCase() === id.trim().toLowerCase());
