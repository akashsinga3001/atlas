# backend/app/enums/fund.py

from enum import Enum as PythonEnum


class FlowType(PythonEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
