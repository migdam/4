"""
Enhancement 3: Salary Parsing and Normalization
"""
import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SalaryInfo:
    """Normalized salary information"""
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = 'USD'
    period: str = 'year'  # 'hour', 'month', 'year'
    original_text: str = ''

    def get_annual_range(self) -> Tuple[Optional[float], Optional[float]]:
        """Convert to annual salary range"""
        multiplier = {
            'hour': 2080,  # 40 hours/week * 52 weeks
            'month': 12,
            'year': 1
        }.get(self.period, 1)

        min_annual = self.min_amount * multiplier if self.min_amount else None
        max_annual = self.max_amount * multiplier if self.max_amount else None

        return min_annual, max_annual

    def get_midpoint(self) -> Optional[float]:
        """Get midpoint of salary range"""
        if self.min_amount and self.max_amount:
            return (self.min_amount + self.max_amount) / 2
        return self.min_amount or self.max_amount

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        min_annual, max_annual = self.get_annual_range()
        return {
            'min': self.min_amount,
            'max': self.max_amount,
            'currency': self.currency,
            'period': self.period,
            'min_annual': min_annual,
            'max_annual': max_annual,
            'midpoint': self.get_midpoint(),
            'original': self.original_text
        }


class SalaryParser:
    """Parse and normalize salary information from text"""

    # Currency symbols and codes
    CURRENCY_MAP = {
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        'zł': 'PLN',
        'pln': 'PLN',
        'usd': 'USD',
        'eur': 'EUR',
        'gbp': 'GBP',
        'chf': 'CHF',
    }

    # Period keywords
    PERIOD_MAP = {
        'hour': 'hour',
        'hourly': 'hour',
        'hr': 'hour',
        '/h': 'hour',
        'month': 'month',
        'monthly': 'month',
        '/mo': 'month',
        '/month': 'month',
        'year': 'year',
        'yearly': 'year',
        'annual': 'year',
        'annually': 'year',
        '/yr': 'year',
        '/year': 'year',
        'pa': 'year',  # per annum
    }

    def parse(self, text: str) -> Optional[SalaryInfo]:
        """Parse salary from text"""
        if not text:
            return None

        text_lower = text.lower().strip()

        # Extract currency
        currency = self._extract_currency(text_lower)

        # Extract period
        period = self._extract_period(text_lower)

        # Extract amounts
        amounts = self._extract_amounts(text)

        if not amounts:
            return None

        # Handle range vs single amount
        if len(amounts) >= 2:
            min_amount = min(amounts[0], amounts[1])
            max_amount = max(amounts[0], amounts[1])
        else:
            min_amount = amounts[0]
            max_amount = None

        return SalaryInfo(
            min_amount=min_amount,
            max_amount=max_amount,
            currency=currency,
            period=period,
            original_text=text
        )

    def _extract_currency(self, text: str) -> str:
        """Extract currency from text"""
        for symbol, code in self.CURRENCY_MAP.items():
            if symbol in text:
                return code
        return 'USD'  # Default

    def _extract_period(self, text: str) -> str:
        """Extract time period from text"""
        for keyword, period in self.PERIOD_MAP.items():
            if keyword in text:
                return period
        return 'year'  # Default to annual

    def _extract_amounts(self, text: str) -> list:
        """Extract numeric amounts from text"""
        # Remove currency symbols
        cleaned = text
        for symbol in ['$', '€', '£', 'zł']:
            cleaned = cleaned.replace(symbol, '')

        # Pattern to match numbers with optional K, M suffixes
        # Matches: 50000, 50,000, 50.5k, 50K, 1.5M
        pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KkMm])?'

        matches = re.findall(pattern, cleaned)
        amounts = []

        for amount_str, multiplier in matches:
            # Remove commas
            amount_str = amount_str.replace(',', '')
            amount = float(amount_str)

            # Apply multiplier
            if multiplier.lower() == 'k':
                amount *= 1_000
            elif multiplier.lower() == 'm':
                amount *= 1_000_000

            amounts.append(amount)

        return amounts

    def compare_salaries(self, salary1: SalaryInfo, salary2: SalaryInfo) -> Dict:
        """Compare two salary offers"""
        min1, max1 = salary1.get_annual_range()
        min2, max2 = salary2.get_annual_range()

        mid1 = salary1.get_midpoint()
        mid2 = salary2.get_midpoint()

        if mid1 and mid2:
            difference = mid2 - mid1
            percentage = (difference / mid1) * 100 if mid1 else 0

            return {
                'salary1_midpoint': mid1,
                'salary2_midpoint': mid2,
                'difference': difference,
                'percentage_difference': percentage,
                'higher': 'salary2' if mid2 > mid1 else 'salary1'
            }

        return {}

    def format_salary(self, salary: SalaryInfo) -> str:
        """Format salary for display"""
        currency_symbol = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'PLN': 'zł'
        }.get(salary.currency, salary.currency)

        if salary.min_amount and salary.max_amount:
            return f"{currency_symbol}{salary.min_amount:,.0f} - {currency_symbol}{salary.max_amount:,.0f} / {salary.period}"
        elif salary.min_amount:
            return f"{currency_symbol}{salary.min_amount:,.0f} / {salary.period}"

        return "Not specified"
