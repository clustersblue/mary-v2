from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_, or_, func
from typing import List, Optional, Any, Dict
from datetime import datetime, date

from app.db.session import get_db
from app.models.finance import MPayroll, MInvoice
from app.models.shift import Transaction, MAttendance, MShift
from app.models.user import User
from app.models.service_user import ServiceUser

router = APIRouter()

# ==============================================================================
# --- 1. PAYMENTS PREVIEW & GENERATION (MaryPayments) ---
# ==============================================================================

@router.get("/getaserviceusertransactions")
async def get_service_user_transactions(
    param: int = Query(0, description="0 = Payroll (by Carer), 1 = Invoice (by Service User)"),
    selectionList: Optional[int] = Query(None, description="Carer ID or Service User ID"),
    dates: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves completed transactions eligible for Payroll or Invoicing generation
    within a selected date range that have not yet been batched.
    """
    try:
        # Default start and end dates if not provided
        start_date_str = "2026-01-01 00:00:00"
        end_date_str = "2026-12-31 23:59:59"

        if dates and len(dates) >= 2:
            start_date_str = f"{dates[0]} 00:00:00"
            end_date_str = f"{dates[1]} 23:59:59"
        elif dates and len(dates) == 1:
            start_date_str = f"{dates[0]} 00:00:00"

        if param == 0:
            # 0 = Payroll (filtered by Carer id)
            filter_clause = "WHERE tx.deleted_at IS NULL AND tx.payroll IS NULL"
            if selectionList:
                filter_clause += f" AND tx.id = {selectionList}"
            filter_clause += f" AND tx.start >= '{start_date_str}' AND tx.start <= '{end_date_str}'"
        else:
            # 1 = Invoice (filtered by Service User su_id)
            filter_clause = "WHERE tx.deleted_at IS NULL AND tx.invoice IS NULL"
            if selectionList:
                filter_clause += f" AND tx.su_id = {selectionList}"
            filter_clause += f" AND tx.start >= '{start_date_str}' AND tx.start <= '{end_date_str}'"

        query = text(f"""
            SELECT 
                tx.tx_id,
                tx.id AS user_id,
                CONCAT(u.first_name, ' ', u.surname) AS carer_full_name,
                tx.su_id,
                CONCAT(su.su_first_name, ' ', su.su_last_name) AS service_user,
                tx.shift_id,
                s.shift,
                tx.start,
                tx.end,
                att.time_in,
                att.time_out,
                COALESCE(tx.rate, sur.rate, 15.00) AS rate,
                COALESCE(sur.invoice, 20.00) AS invoice_rate,
                TIMESTAMPDIFF(MINUTE, tx.start, tx.end) AS duration_minutes,
                tx.created_at,
                tx.updated_at
            FROM m_transactions tx
            JOIN users u ON tx.id = u.id
            JOIN m_service_users su ON tx.su_id = su.su_id
            LEFT JOIN m_shifts s ON tx.shift_id = s.shift_id
            LEFT JOIN m_attendances att ON tx.tx_id = att.tx_id AND att.deleted_at IS NULL
            LEFT JOIN m_service_user_rates sur ON tx.su_id = sur.su_id AND tx.shift_id = sur.shift_id AND sur.deleted_at IS NULL
            {filter_clause}
            ORDER BY tx.start ASC
            LIMIT 500
        """)

        result = await db.execute(query)
        rows = result.fetchall()

        data = []
        for r in rows:
            time_in_obj = r[9] if r[9] else r[7]
            time_out_obj = r[10] if r[10] else r[8]

            if time_in_obj and time_out_obj:
                try:
                    diff_secs = (time_out_obj - time_in_obj).total_seconds()
                    if diff_secs < 0:
                        diff_secs += 86400  # overnight shift
                    duration_mins = int(diff_secs // 60)
                except Exception:
                    duration_mins = r[13] or 60
            else:
                duration_mins = r[13] or 60

            hours_val = round(duration_mins / 60.0, 2)
            rate_val = float(r[11] or 15.00)
            inv_rate_val = float(r[12] or 20.00)

            data.append({
                "tx_id": r[0],
                "id": r[1],
                "user_id": r[1],
                "carer_full_name": r[2] or "Carer Staff",
                "su_id": r[3],
                "service_user": r[4] or "Service User",
                "su_full_name": r[4] or "Service User",
                "shift_id": r[5],
                "shift": r[6] or "Standard Shift",
                "start": r[7].isoformat() if r[7] else None,
                "end": r[8].isoformat() if r[8] else None,
                "time_in": r[9].isoformat() if r[9] else (r[7].isoformat() if r[7] else None),
                "time_out": r[10].isoformat() if r[10] else (r[8].isoformat() if r[8] else None),
                "total_time": f"{duration_mins // 60:02d}:{duration_mins % 60:02d}",
                "rate": rate_val,
                "invoice": inv_rate_val,
                "hours": f"{hours_val:.2f}",
                "amount": round(hours_val * rate_val, 2),
                "invoice_amount": round(hours_val * inv_rate_val, 2),
                "created_at": r[14].isoformat() if r[14] else None,
                "updated_at": r[15].isoformat() if r[15] else None
            })

        return {"message": True, "data": data}
    except Exception as e:
        return {"message": False, "data": str(e)}

@router.post("/generatepayments")
async def generate_payments(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Generates batches of Payroll (param = 0) or Invoices (param = 1),
    creates tracking records, and stamps transactions.
    """
    user_id = payload.get("user_id", 1)
    param = int(payload.get("param", 0))
    date_range = payload.get("date_range", "")
    items = payload.get("data", [])

    if not items:
        raise HTTPException(status_code=400, detail="No transactions provided for payment generation.")

    now_str = datetime.now().strftime("%m%d%Y")
    first_item = items[0]

    if param == 0:
        # Generate Payroll Batch
        carer_id = first_item.get("id") or first_item.get("user_id") or 1
        batch_number = f"P{now_str}{int(carer_id):05d}"

        for item in items:
            tx_id = item.get("tx_id")
            rate_val = float(item.get("rate") or 0.0)

            # Insert into m_payrolls
            payroll_entry = MPayroll(
                tx_id=tx_id,
                payroll_number=batch_number,
                payment=None,
                rate=rate_val,
                notes=f"Payroll batch generated for transaction {tx_id}",
                generated=user_id,
                processed=None,
                date_range=date_range
            )
            db.add(payroll_entry)

            # Update m_transactions
            await db.execute(
                text("UPDATE m_transactions SET payroll = :batch WHERE tx_id = :tx_id"),
                {"batch": batch_number, "tx_id": tx_id}
            )

        await db.commit()
        return {
            "message": True,
            "data": f"Payroll batch {batch_number} generated successfully for {len(items)} shifts."
        }
    else:
        # Generate Invoice Batch
        su_id = first_item.get("su_id") or 1
        batch_number = f"I{now_str}{int(su_id):05d}"

        for item in items:
            tx_id = item.get("tx_id")
            invoice_val = float(item.get("invoice") or item.get("invoice_amount") or 0.0)

            # Insert into m_invoices
            invoice_entry = MInvoice(
                tx_id=tx_id,
                invoice_number=batch_number,
                payment=None,
                invoice=invoice_val,
                notes=f"Invoice batch generated for transaction {tx_id}",
                generated=user_id,
                processed=None,
                date_range=date_range
            )
            db.add(invoice_entry)

            # Update m_transactions
            await db.execute(
                text("UPDATE m_transactions SET invoice = :batch WHERE tx_id = :tx_id"),
                {"batch": batch_number, "tx_id": tx_id}
            )

        await db.commit()
        return {
            "message": True,
            "data": f"Invoice batch {batch_number} generated successfully for {len(items)} visits."
        }


# ==============================================================================
# --- 2. PAYROLL MANAGEMENT (MaryPayroll) ---
# ==============================================================================

@router.get("/getpayrolls")
async def get_payrolls(
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns active (data1: unfinalized) and historical (data2: all) payroll items.
    """
    user_filter = f"AND u.id = {user_id}" if user_id else ""

    base_query = f"""
        SELECT 
            p.payroll_id,
            p.payroll_number,
            p.tx_id,
            p.payment,
            p.generated,
            p.processed,
            p.date_range,
            p.notes,
            u.id AS user_id,
            CONCAT(u.first_name, ' ', u.surname) AS carer_full_name,
            u.ni_num,
            su.su_id,
            CONCAT(su.su_first_name, ' ', su.su_last_name) AS service_user,
            s.shift,
            tx.start,
            tx.end,
            COALESCE(p.rate, tx.rate, sur.rate, 15.00) AS rate,
            TIMESTAMPDIFF(MINUTE, tx.start, tx.end) AS duration_minutes,
            att.time_in,
            att.time_out,
            p.created_at
        FROM m_payrolls p
        JOIN m_transactions tx ON p.tx_id = tx.tx_id
        JOIN users u ON tx.id = u.id
        JOIN m_service_users su ON tx.su_id = su.su_id
        LEFT JOIN m_shifts s ON tx.shift_id = s.shift_id
        LEFT JOIN m_attendances att ON tx.tx_id = att.tx_id AND att.deleted_at IS NULL
        LEFT JOIN m_service_user_rates sur ON tx.su_id = sur.su_id AND tx.shift_id = sur.shift_id AND sur.deleted_at IS NULL
        WHERE p.deleted_at IS NULL
        {user_filter}
    """

    # data1: Unfinalized (payment is null)
    query_unpaid = text(base_query + " AND p.payment IS NULL ORDER BY p.payroll_number DESC, tx.start ASC")
    # data2: All history
    query_history = text(base_query + " ORDER BY p.payroll_number DESC, tx.start ASC LIMIT 500")

    res_unpaid = await db.execute(query_unpaid)
    res_history = await db.execute(query_history)

    def format_rows(rows):
        formatted = []
        for r in rows:
            duration_mins = r[17] or 60
            hours_val = round(duration_mins / 60.0, 2)
            rate_val = float(r[16] or 15.00)
            formatted.append({
                "payroll_id": r[0],
                "payroll_number": r[1],
                "tx_id": r[2],
                "payment": r[3].isoformat() if r[3] else None,
                "generated": r[4],
                "processed": r[5],
                "date_range": r[6] or "",
                "notes": r[7] or "",
                "id": r[8],
                "user_id": r[8],
                "carer_full_name": r[9] or "Carer Staff",
                "ni_num": r[10] or "N/A",
                "su_id": r[11],
                "service_user": r[12] or "Service User",
                "shift": r[13] or "Standard Shift",
                "start": r[14].isoformat() if r[14] else None,
                "start_date": r[14].strftime("%d-%m-%Y") if hasattr(r[14], "strftime") else (str(r[14])[:10] if r[14] else ""),
                "end": r[15].isoformat() if r[15] else None,
                "rate": rate_val,
                "hours": f"{hours_val:.2f}",
                "amount": round(hours_val * rate_val, 2),
                "time_in": r[18].isoformat() if r[18] else None,
                "time_out": r[19].isoformat() if r[19] else None,
                "created_at": r[20].isoformat() if r[20] else None
            })
        return formatted

    return {
        "data1": format_rows(res_unpaid.fetchall()),
        "data2": format_rows(res_history.fetchall()),
        "message": "Payroll records retrieved successfully"
    }

@router.post("/markpayrolls")
async def mark_payrolls(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Marks selected payroll records as Paid and updates attendance timestamps.
    """
    user_id = payload.get("user_id", 1)
    records = payload.get("data", [])
    now = datetime.utcnow()

    for rec in records:
        payroll_number = rec.get("payroll_number")
        tx_id = rec.get("tx_id")

        if payroll_number and tx_id:
            await db.execute(
                text("""
                    UPDATE m_payrolls 
                    SET payment = :now, processed = :user_id 
                    WHERE payroll_number = :num AND tx_id = :tx_id
                """),
                {"now": now, "user_id": user_id, "num": payroll_number, "tx_id": tx_id}
            )

            # Mark attendance paid
            await db.execute(
                text("UPDATE m_attendances SET paid = :now WHERE tx_id = :tx_id"),
                {"now": now, "tx_id": tx_id}
            )

    await db.commit()
    return {"success": True, "data": "Payroll marked as Paid successfully"}

@router.post("/deletepayroll")
async def delete_payroll(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Voids a payroll batch: soft-deletes m_payrolls and resets m_transactions.payroll to NULL.
    """
    user_id = payload.get("user_id", 1)
    payroll_number = payload.get("data")
    now = datetime.utcnow()

    if not payroll_number:
        raise HTTPException(status_code=400, detail="Payroll batch number required.")

    # Soft delete payroll entries
    res = await db.execute(
        text("UPDATE m_payrolls SET deleted_at = :now, processed = :user_id WHERE payroll_number = :num"),
        {"now": now, "user_id": user_id, "num": payroll_number}
    )
    rows_deleted = res.rowcount

    # Unlink transactions
    await db.execute(
        text("UPDATE m_transactions SET payroll = NULL WHERE payroll = :num"),
        {"num": payroll_number}
    )

    await db.commit()
    return {
        "success": True,
        "data": f"{rows_deleted} records in Payroll {payroll_number} voided successfully."
    }

@router.post("/updatetransactionrate/{tx_id}")
async def update_transaction_rate(
    tx_id: int,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the pay rate for a transaction and associated payroll record.
    """
    rate = payload.get("rate")
    if rate is None:
        raise HTTPException(status_code=400, detail="Rate value required.")
    
    rate_val = float(rate)
    await db.execute(
        text("UPDATE m_transactions SET rate = :rate WHERE tx_id = :tx_id"),
        {"rate": rate_val, "tx_id": tx_id}
    )
    await db.execute(
        text("UPDATE m_payrolls SET rate = :rate WHERE tx_id = :tx_id"),
        {"rate": rate_val, "tx_id": tx_id}
    )
    await db.commit()
    return {"success": True, "message": "Transaction rate updated successfully"}


# ==============================================================================
# --- 3. INVOICE MANAGEMENT (MaryInvoice) ---
# ==============================================================================

@router.get("/getinvoices")
async def get_invoices(
    su_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns active (data1: uncollected) and historical (data2: all) invoice items.
    """
    su_filter = f"AND su.su_id = {su_id}" if su_id else ""

    base_query = f"""
        SELECT 
            inv.invoice_id,
            inv.invoice_number,
            inv.tx_id,
            inv.payment,
            inv.generated,
            inv.processed,
            inv.date_range,
            inv.notes,
            su.su_id,
            su.su_number,
            CONCAT(su.su_first_name, ' ', su.su_last_name) AS service_user,
            su.home_address,
            u.id AS user_id,
            CONCAT(u.first_name, ' ', u.surname) AS carer_full_name,
            s.shift,
            tx.start,
            tx.end,
            COALESCE(inv.invoice, sur.invoice, 20.00) AS invoice_rate,
            TIMESTAMPDIFF(MINUTE, tx.start, tx.end) AS duration_minutes,
            att.time_in,
            att.time_out,
            inv.created_at
        FROM m_invoices inv
        JOIN m_transactions tx ON inv.tx_id = tx.tx_id
        JOIN m_service_users su ON tx.su_id = su.su_id
        JOIN users u ON tx.id = u.id
        LEFT JOIN m_shifts s ON tx.shift_id = s.shift_id
        LEFT JOIN m_attendances att ON tx.tx_id = att.tx_id AND att.deleted_at IS NULL
        LEFT JOIN m_service_user_rates sur ON tx.su_id = sur.su_id AND tx.shift_id = sur.shift_id AND sur.deleted_at IS NULL
        WHERE inv.deleted_at IS NULL
        {su_filter}
    """

    query_unpaid = text(base_query + " AND inv.payment IS NULL ORDER BY inv.invoice_number DESC, tx.start ASC")
    query_history = text(base_query + " ORDER BY inv.invoice_number DESC, tx.start ASC LIMIT 500")

    res_unpaid = await db.execute(query_unpaid)
    res_history = await db.execute(query_history)

    def format_invoice_rows(rows):
        formatted = []
        for r in rows:
            duration_mins = r[18] or 60
            hours_val = round(duration_mins / 60.0, 2)
            inv_rate_val = float(r[17] or 20.00)
            formatted.append({
                "invoice_id": r[0],
                "invoice_number": r[1],
                "tx_id": r[2],
                "payment": r[3].isoformat() if r[3] else None,
                "generated": r[4],
                "processed": r[5],
                "date_range": r[6] or "",
                "notes": r[7] or "",
                "su_id": r[8],
                "su_number": r[9] or "SU-001",
                "service_user": r[10] or "Service User",
                "address": r[11] or "",
                "home_address": r[11] or "",
                "user_id": r[12],
                "carer_full_name": r[13] or "Carer Staff",
                "shift": r[14] or "Care Visit",
                "start": r[15].isoformat() if r[15] else None,
                "start_date": r[15].strftime("%d-%m-%Y") if hasattr(r[15], "strftime") else (str(r[15])[:10] if r[15] else ""),
                "end": r[16].isoformat() if r[16] else None,
                "invoice": inv_rate_val,
                "invoice_rate": inv_rate_val,
                "hours": f"{hours_val:.2f}",
                "amount": round(hours_val * inv_rate_val, 2),
                "time_in": r[19].isoformat() if r[19] else None,
                "time_out": r[20].isoformat() if r[20] else None,
                "created_at": r[21].isoformat() if r[21] else None
            })
        return formatted

    return {
        "data1": format_invoice_rows(res_unpaid.fetchall()),
        "data2": format_invoice_rows(res_history.fetchall()),
        "message": "Invoice records retrieved successfully"
    }

@router.post("/markinvoices")
async def mark_invoices(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Marks selected invoice records as Paid / Settled.
    """
    user_id = payload.get("user_id", 1)
    records = payload.get("data", [])
    now = datetime.utcnow()

    for rec in records:
        invoice_number = rec.get("invoice_number")
        tx_id = rec.get("tx_id")

        if invoice_number and tx_id:
            await db.execute(
                text("""
                    UPDATE m_invoices 
                    SET payment = :now, processed = :user_id 
                    WHERE invoice_number = :num AND tx_id = :tx_id
                """),
                {"now": now, "user_id": user_id, "num": invoice_number, "tx_id": tx_id}
            )

    await db.commit()
    return {"success": True, "data": "Invoices marked as Settled successfully"}

@router.post("/deleteinvoice")
async def delete_invoice(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Voids an invoice batch: soft-deletes m_invoices and resets m_transactions.invoice to NULL.
    """
    user_id = payload.get("user_id", 1)
    invoice_number = payload.get("data")
    now = datetime.utcnow()

    if not invoice_number:
        raise HTTPException(status_code=400, detail="Invoice batch number required.")

    res = await db.execute(
        text("UPDATE m_invoices SET deleted_at = :now, processed = :user_id WHERE invoice_number = :num"),
        {"now": now, "user_id": user_id, "num": invoice_number}
    )
    rows_deleted = res.rowcount

    await db.execute(
        text("UPDATE m_transactions SET invoice = NULL WHERE invoice = :num"),
        {"num": invoice_number}
    )

    await db.commit()
    return {
        "success": True,
        "data": f"{rows_deleted} records in Invoice {invoice_number} voided successfully."
    }
