"""
Database tracking for emails and costs
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

import config


class EmailDeliveryTracker:
    """Track email delivery attempts and status"""

    def __init__(self, db_path: Path = config.EMAIL_DELIVERY_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                sent_at TIMESTAMP,
                status TEXT NOT NULL,
                attempts INTEGER DEFAULT 1,
                message_id TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def log_email_attempt(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        status: str,
        attempts: int = 1,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> int:
        """Log an email delivery attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sent_at = datetime.now() if status == "sent" else None

        cursor.execute("""
            INSERT INTO email_deliveries
            (recipient_email, recipient_name, subject, sent_at, status, attempts, message_id, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (recipient_email, recipient_name, subject, sent_at, status, attempts, message_id, error_message))

        delivery_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return delivery_id

    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM email_deliveries
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            'total': row[0] or 0,
            'sent': row[1] or 0,
            'failed': row[2] or 0
        }


class CostTracker:
    """Track API usage costs"""

    def __init__(self, db_path: Path = config.COST_TRACKING_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                service TEXT NOT NULL,
                operation TEXT NOT NULL,
                units_used REAL NOT NULL,
                estimated_cost REAL NOT NULL,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    def log_usage(
        self,
        service: str,
        operation: str,
        units_used: float,
        estimated_cost: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log API usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute("""
            INSERT INTO api_usage (service, operation, units_used, estimated_cost, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (service, operation, units_used, estimated_cost, metadata_json))

        conn.commit()
        conn.close()

    def get_total_costs(self, service: Optional[str] = None) -> Dict[str, Any]:
        """Get total costs, optionally filtered by service"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if service:
            cursor.execute("""
                SELECT
                    service,
                    COUNT(*) as operations,
                    SUM(units_used) as total_units,
                    SUM(estimated_cost) as total_cost
                FROM api_usage
                WHERE service = ?
                GROUP BY service
            """, (service,))
        else:
            cursor.execute("""
                SELECT
                    service,
                    COUNT(*) as operations,
                    SUM(units_used) as total_units,
                    SUM(estimated_cost) as total_cost
                FROM api_usage
                GROUP BY service
            """)

        results = cursor.fetchall()
        conn.close()

        costs_by_service = {}
        total_cost = 0.0

        for row in results:
            service_name = row[0]
            costs_by_service[service_name] = {
                'operations': row[1],
                'units': row[2],
                'cost': row[3]
            }
            total_cost += row[3]

        return {
            'by_service': costs_by_service,
            'total_cost': total_cost
        }

    def log_openai_usage(self, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4o-mini"):
        """Log OpenAI API usage with cost estimation"""
        # Pricing as of 2024 (per 1M tokens)
        pricing = {
            "gpt-4o-mini": {"input": 0.150, "output": 0.600},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00}
        }

        rates = pricing.get(model, pricing["gpt-4o-mini"])

        input_cost = (prompt_tokens / 1_000_000) * rates["input"]
        output_cost = (completion_tokens / 1_000_000) * rates["output"]
        total_cost = input_cost + output_cost

        self.log_usage(
            service="OpenAI",
            operation=model,
            units_used=prompt_tokens + completion_tokens,
            estimated_cost=total_cost,
            metadata={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "model": model
            }
        )

    def log_bright_data_search(self, num_queries: int):
        """Log Bright Data search usage"""
        # Estimate: Assume $0.01 per search query
        cost_per_query = 0.01
        total_cost = num_queries * cost_per_query

        self.log_usage(
            service="BrightData",
            operation="search",
            units_used=num_queries,
            estimated_cost=total_cost,
            metadata={"queries": num_queries}
        )

    def log_bright_data_scrape(self, num_urls: int):
        """Log Bright Data scrape usage"""
        # Estimate: Assume $0.005 per URL scrape
        cost_per_scrape = 0.005
        total_cost = num_urls * cost_per_scrape

        self.log_usage(
            service="BrightData",
            operation="scrape",
            units_used=num_urls,
            estimated_cost=total_cost,
            metadata={"urls_scraped": num_urls}
        )
