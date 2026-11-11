# Personal guest invitations and QR passes

In Guests, the organiser or a co-organiser with guest permission chooses **Create invitation** and enters the guest's name. Google email is optional. For an existing guest, choose **Share invitation** in their row.

The app generates a complete message containing the guest's name, wedding name/date/venue, the functions with their dates and 12-hour times, the personal RSVP link, the plus-one allowance and RSVP instructions. The co-organiser can edit the message before copying or sharing it. **Share on WhatsApp** opens a prepared message; **Share anywhere** uses the phone's share sheet if supported. These are user-triggered shares and do not need Twilio or a WhatsApp Business account. No messages are sent automatically.

Two QR codes are prepared:

- Invitation QR opens the private invitation link and Guest login.
- Wedding entry QR is a signed pass specific to the wedding and guest. The gate rejects it until the guest confirms their RSVP. Existing single-entry and plus-one checks still apply.

QR downloads are PNG images for easy attachment to messages. The phone's native share sheet can include the entry QR image when file sharing is supported; otherwise copy the message or attach a downloaded PNG manually.

The invited guest opens the link, sees a personalised welcome and chooses **Guest login**. They continue with Google and are taken directly to that wedding's guest Passport, without typing an event code or waiting for a second approval. The invitation token is remembered only in the current tab during the OAuth round trip and cleared once claimed. Google credentials and tokens are not stored in browser storage.

If an invited Google email is supplied, only that verified email may claim the invitation. For a name-only invitation, the first eligible Google account that uses the private link claims the guest entry. The verified email is then saved on the guest entry; the link cannot be used by a second account. Share name-only links privately. A signed-in organiser cannot use a guest invitation to change their own role in the same wedding. Existing memberships in other weddings remain scoped and unchanged.

The guest sees only their own family and invitation data plus the wedding information available to guests. They can RSVP Yes/No for the next function, choose other functions and provide their family, dietary and stay details within organiser-set limits. Their personal pass is available in the portal after RSVP confirmation. They can return later through ordinary Google sign-in.

**Replace this private invitation link** invalidates the old link and old printed QR passes. It preserves existing guest account access. Owner revocation invalidates the invitation and entry nonce and blocks the guest's account. Expired or replaced invitations show a request for a new link. Private links last until at least 180 days after issue or 30 days after the wedding date, whichever is later; an existing guest account remains until access is revoked.

Invitation records use a new private database table, created by the additive migration. PostgreSQL row-level security and existing schema privileges apply. Public previews expose only the invitation's guest name and basic wedding details, never financial information, email addresses, other guests or the signed entry token. Mutations require authenticated, authorised sessions and CSRF protection. Claims, replacement and revocation are serialised so two accounts cannot take the same invitation.

## Entering times

Time fields now have separate Hour (1–12), Minute (00–59) and AM/PM selectors. All three must be selected for a new time. Midnight is stored as 00:xx and noon as 12:xx, preserving the existing backend sorting and India-time next-function selection. Timelines, guest function details and invitation messages show 12-hour times.
