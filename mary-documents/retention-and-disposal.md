# Retention and disposal

This is a design for St Mary's Team Carers Ltd. It is not a deletion feature.

The Mary Care software keeps service-user, visit, note, medication, document, invoice, payroll, and access-log records until an authorised person disposes of them. It does not delete care records on a schedule. It does not provide an erasure button. Building either of those would remove records the agency may have a duty to keep.

## What is kept

| Record | Where it lives | Disposal note |
| --- | --- | --- |
| Service user, next of kin, and contacts | Service-user record | Dispose only after the schedule below and a manager's approval |
| Visits, care notes, conditions, and medications | Visit and care records, including generated care-note files | The file and the database row both have to be included |
| Uploaded care documents | Stored files and the uploaded-file row | Delete the file as well as the row |
| Invoices and payroll | Finance records | Keep for the finance period the agency confirms |
| Access log | Access-log table | Keep at least as long as the records the log describes |
| Access-request reason | Access-log row for that export | Stays on the access log. It is not printed in the copy given to the requester |

The previous privacy notice mentioned an eight-year period. That period is not enforced by the software. The agency should confirm its own schedule before the first disposal. The periods below are the working schedule until that confirmation changes them.

## Working schedule

- Adult care records: keep for 8 years after the last contact with the service user.
- Children's care records: keep for longer than the adult period. Do not use the adult period for a child. Confirm the end date with the agency's adviser before disposal.
- Staff and carer employment records: keep for about 6 years after employment ends.
- Access-log rows: keep at least as long as the care or staff record they describe. Do not delete a log row while the record it describes is still held.
- Access-request reasons: keep with the access-log row. Do not shorten that row because the reason is sensitive.

## Disposal steps

1. Identify the record, the service user or staff member, and the last contact or employment end date.
2. Check this schedule. If the record is still inside the period, stop.
3. A manager records approval. Approval names the record and the date. It does not copy clinical text.
4. Delete the database rows and the stored files for that record. Deleting a row and leaving the file in storage is not disposal.
5. Write a disposal record: date, approver, record type, and the service-user or staff identifier. Do not copy clinical content, medication text, or the access-request reason into the disposal record.
6. Leave the access-log rows in place until they themselves reach the end of their retention period.

No scheduled job and no Article 17 control implements these steps. A person follows them.

## What this design does not do

- It does not decide the lawful reason for keeping a record.
- It does not erase a record because someone asked, where a retention duty still applies.
- It does not backfill or rewrite older access-log rows that have no staff identity.
