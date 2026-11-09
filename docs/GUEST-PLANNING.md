# Guest family planning and vendor payments

## Guest Passport

“Save you a seat?” asks Yes or No for the nearest upcoming function, using India time. Guests also see the full timeline and tick every function their family will attend. Unticked functions are saved as No, and confirming any function confirms the family RSVP. Guests can change these answers later. Every new function appears on the timeline immediately; guests can update their saved selection to include it.

The family count includes the primary guest. Each named person has a diet dropdown, origin and optional dietary/allergy notes. The guest can add family origin, arrival/departure dates, requested rooms, a hotel from the organiser's booked hotel list, or their own accommodation. Room numbers are guest-reported assigned numbers; entering one does not allocate inventory or confirm a booking. Guests see only their own family information and public hotel names, addresses and check-in times.

Co-organisers with `hotels` permission add booked hotels from Travel & stay. Co-organisers with `timeline` permission add celebrations from Timeline; there is no app-imposed function count limit. All functions are visible to guests, including functions not on their original invitation.

## Settings → Manage guest limits

The owner or a co-organiser with `guests` permission can set the new-invitation default, maximum plus-ones, total family-size limit, maximum requested rooms and each guest's allowance. Family size includes the primary guest. Defaults affect new invitations; existing invitations retain their allowance subject to the overall caps. Defaults are zero plus-ones, maximum 20 plus-ones, family size 21 and 10 requested rooms. The server validates the limits, including old RSVP requests. A limit below a confirmed RSVP is rejected; coordinate an updated RSVP first.

The guest list shows hotel, room number, arrival and room requests. Open Family & function details for every family member, diet and function response. Catering counts confirmed family members rather than invitation rows, and named members' dietary preferences.

## Vendor payments

Owners, finance members, and co-organisers with `vendors` permission can access the vendor payment panel. Finance has Vendors in navigation and the same panel in Expenses. Save a verified UPI ID, payee name, optional bank name, account last four digits, IFSC and notes. Do not store full bank account numbers here.

Pay vendor prepares a UPI intent for the entered amount, bounded by the outstanding quote. On a phone with a supported UPI app, open the handoff and verify the vendor and amount. Demo mode only previews this step and never opens a payment app. Opening UPI never increases the recorded paid amount.

After checking that payment actually completed, use Record completed payment with an amount, method and transaction/receipt reference. The record is explicitly marked Recorded manually. Vendor paid/balance and transaction history update together; duplicate requests do not count twice. Vendor records remain separate from expense entries: reconcile the expense ledger when recording vendor transactions. No provider confirmation is implied by a manual record.

Razorpay vendor transfers remain deferred. Standard Razorpay Checkout collects money into a merchant account and is not a vendor payout mechanism. Future automated vendor transfers need Razorpay Route/linked accounts or a payout product, appropriate account approval, server-side verification, reconciliation and webhooks. Existing Event Pass purchase checkout remains separate. Adding ordinary checkout keys alone does not enable vendor transfers.

All new information uses the existing event-scoped database records. No schema migration or new external account is required for these flows.
