# Sample requests

Administrative workflow: requested → preparing → sent → delivered → evaluated. Cancellation is possible before dispatch. Buyer feedback is approved, rejected or retest; no sale is created automatically.

Each request links one CRM company and product, optionally an active supplier offer for that product. Names are captured from canonical records and retained as historical snapshots. Referenced records cannot be deleted, including after cancellation. Portfolio replacement is blocked while sample requests exist.

Quantity and unit are explicit sample measurements, independent of catalogue units. Lot, packaging, recipient, destination, carrier, tracking and dates are manual records, not carrier integration or lot traceability. No stock movement, reservation, financial entry, invoice, shipping contract or Siscomex submission occurs. Blank cost means unknown; currencies are not combined.

Only current database administrators may list, read, create, edit, transition or read history. Writes use the existing business lease and optimistic versions. Dispatch freezes physical shipment terms. Actual dates cannot be future or out of sequence. Evaluated and cancelled requests are final.

History uses the existing bounded hash-linked archive and signed pagination. Lists omit private notes, addresses, costs and history. Individual records retain those fields for administrators. No customer documents or credentials should be entered into free text.

The separate development branch does not update an installed Docker stack or import existing data. Existing installation remains unchanged until a later explicit update after the ongoing import is complete.
