import pandas as pd
import io
from typing import List, Dict, Any

def parse_dtr_excel(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parses a DTR Excel file into a list of shift attendance records using pandas and openpyxl.
    """
    df = pd.read_excel(io.BytesIO(file_bytes))
    
    # Normalize column headers
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    
    records = []
    for _, row in df.iterrows():
        records.append({
            "carer_id": row.get("carer_id") or row.get("user_id"),
            "carer_name": str(row.get("carer_name") or row.get("staff_name") or "Unknown"),
            "date": str(row.get("date") or row.get("shift_date") or ""),
            "time_in": str(row.get("time_in") or row.get("clock_in") or ""),
            "time_out": str(row.get("time_out") or row.get("clock_out") or ""),
            "status": str(row.get("status") or "imported")
        })
        
    return records
