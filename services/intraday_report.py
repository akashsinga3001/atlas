"""HTML report generation for intraday execution runs."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any


class IntradayReportService:
    """Build a detailed HTML report for the intraday execution pipeline."""

    def build_html(self, pipeline_result: dict[str, Any]) -> str:
        """Return a complete HTML report body for one intraday run."""
        run_date = self._as_text(pipeline_result.get('run_date'))
        snapshot = pipeline_result.get('snapshot', {}) if isinstance(pipeline_result.get('snapshot', {}), dict) else {}
        features = pipeline_result.get('features', {}) if isinstance(pipeline_result.get('features', {}), dict) else {}
        inference = pipeline_result.get('inference', {}) if isinstance(pipeline_result.get('inference', {}), dict) else {}
        orders = pipeline_result.get('orders', {}) if isinstance(pipeline_result.get('orders', {}), dict) else {}
        summary = pipeline_result.get('order_summary', {}) if isinstance(pipeline_result.get('order_summary', {}), dict) else {}

        top_long = inference.get('top_long', []) if isinstance(inference, dict) else []
        top_short = inference.get('top_short', []) if isinstance(inference, dict) else []
        responses = orders.get('responses', []) if isinstance(orders, dict) else []
        reject_counts = summary.get('reject_counts', {}) if isinstance(summary, dict) else {}

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Atlas Intraday Execution Report - {escape(run_date)}</title>
</head>
<body style='font-family: Segoe UI, Arial, sans-serif; background:#f4f6fb; color:#1f2937; margin:0; padding:24px;'>
  <div style='max-width:1200px; margin:0 auto; background:#ffffff; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.06); overflow:hidden;'>
    <div style='background:#111827; color:#ffffff; padding:20px 24px;'>
      <h1 style='margin:0; font-size:24px;'>Atlas Intraday Execution Report</h1>
      <p style='margin:8px 0 0;'>Run Date: {escape(run_date)}</p>
    </div>

    <div style='padding:20px 24px;'>
      <h2 style='margin:0 0 12px; font-size:20px;'>Run Summary</h2>
      {self._summary_table(pipeline_result, summary)}

      <h2 style='margin:20px 0 12px; font-size:20px;'>Signals Generated</h2>
      {self._signals_table(top_long, top_short)}

      <h2 style='margin:20px 0 12px; font-size:20px;'>Order Attempts</h2>
      {self._orders_table(responses)}

      <h2 style='margin:20px 0 12px; font-size:20px;'>Rejection Reasons</h2>
      {self._rejects_table(reject_counts)}
    </div>
  </div>
</body>
</html>
        """.strip()

    def _summary_table(self, pipeline_result: dict[str, Any], summary: dict[str, Any]) -> str:
        snapshot = pipeline_result.get('snapshot', {}) if isinstance(pipeline_result.get('snapshot', {}), dict) else {}
        features = pipeline_result.get('features', {}) if isinstance(pipeline_result.get('features', {}), dict) else {}
        inference = pipeline_result.get('inference', {}) if isinstance(pipeline_result.get('inference', {}), dict) else {}
        orders = pipeline_result.get('orders', {}) if isinstance(pipeline_result.get('orders', {}), dict) else {}

        rows = [
            ('Snapshot processed', snapshot.get('processed', snapshot.get('inserted_or_updated', '-'))),
            ('Features processed', features.get('candles_processed', features.get('inserted_or_updated', '-'))),
            ('Signals generated', len(inference.get('top_long', [])) + len(inference.get('top_short', []))),
            ('Orders attempted', len(orders.get('responses', []))),
            ('Orders submitted', orders.get('submitted', 0)),
            ('Open positions', summary.get('open_positions_count', '-')),
            ('Available slots', summary.get('available_slots', '-')),
            ('Available funds', summary.get('available_funds', '-')),
            ('Reserve', summary.get('reserve', '-')),
            ('Deployable funds', summary.get('deployable', '-')),
        ]

        body = ["<table style='width:100%; border-collapse:collapse; margin-bottom:8px;'><tr style='background:#e2e8f0;'><th style='text-align:left; padding:10px;'>Metric</th><th style='text-align:left; padding:10px;'>Value</th></tr>"]
        for label, value in rows:
            body.append(f"<tr><td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(str(label))}</td><td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(value))}</td></tr>")
        body.append('</table>')
        return ''.join(body)

    def _signals_table(self, top_long: list[dict[str, Any]], top_short: list[dict[str, Any]]) -> str:
        rows = []
        for direction, items in (('long', top_long), ('short', top_short)):
            for row in items:
                rows.append(
                    f"<tr>"
                    f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(direction)}</td>"
                    f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(row.get('rank', '-')))}</td>"
                    f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(row.get('ticker', '-')))}</td>"
                    f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{float(row.get('confidence', 0.0)):.4f}</td>"
                    f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._format_drivers(row.get('top_features', [])))}</td>"
                    f"</tr>"
                )

        if not rows:
            return "<div style='padding:10px; background:#f9fafb; border:1px solid #e5e7eb;'>No signals generated.</div>"

        return (
            "<table style='width:100%; border-collapse:collapse; margin-bottom:8px;'>"
            "<tr style='background:#e2e8f0;'>"
            "<th style='text-align:left; padding:10px;'>Direction</th>"
            "<th style='text-align:left; padding:10px;'>Rank</th>"
            "<th style='text-align:left; padding:10px;'>Ticker</th>"
            "<th style='text-align:left; padding:10px;'>Confidence</th>"
            "<th style='text-align:left; padding:10px;'>Top Drivers</th>"
            "</tr>"
            + ''.join(rows)
            + '</table>'
        )

    def _orders_table(self, responses: list[dict[str, Any]]) -> str:
        if not responses:
            return "<div style='padding:10px; background:#f9fafb; border:1px solid #e5e7eb;'>No order attempts were made.</div>"

        rows: list[str] = []
        for item in responses:
            request = item.get('request', {}) if isinstance(item, dict) else {}
            response = item.get('response', {}) if isinstance(item, dict) else {}
            order = request.get('order', {}) if isinstance(request, dict) else {}
            status = 'success' if item.get('success') else 'failed'
            reason = self._response_reason(response)
            order_id = self._as_text(response.get('order_id', '-')) if isinstance(response, dict) else '-'
            rows.append(
                f"<tr>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(request.get('underlying', '-')))}</td>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(request.get('direction', '-')))}</td>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(order.get('order_type', '-')))}</td>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(order.get('tradingsymbol', '-')))}</td>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(status)}</td>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(order_id)}</td>"
                f"<td style='padding:10px; border-bottom:1px solid #e5e7eb;'>{escape(reason)}</td>"
                f"</tr>"
            )

        return (
            "<table style='width:100%; border-collapse:collapse; margin-bottom:8px;'>"
            "<tr style='background:#e2e8f0;'>"
            "<th style='text-align:left; padding:10px;'>Underlying</th>"
            "<th style='text-align:left; padding:10px;'>Direction</th>"
            "<th style='text-align:left; padding:10px;'>Order Type</th>"
            "<th style='text-align:left; padding:10px;'>Contract</th>"
            "<th style='text-align:left; padding:10px;'>Status</th>"
            "<th style='text-align:left; padding:10px;'>Order ID</th>"
            "<th style='text-align:left; padding:10px;'>Failure Reason</th>"
            "</tr>"
            + ''.join(rows)
            + '</table>'
        )

    def _rejects_table(self, reject_counts: dict[str, Any]) -> str:
        if not reject_counts:
            return "<div style='padding:10px; background:#f9fafb; border:1px solid #e5e7eb;'>No filter rejections recorded.</div>"

        rows = []
        for key, value in reject_counts.items():
            rows.append(f"<tr><td style='padding:8px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(key))}</td><td style='padding:8px; border-bottom:1px solid #e5e7eb;'>{escape(self._as_text(value))}</td></tr>")

        return (
            "<table style='width:100%; border-collapse:collapse; margin-bottom:8px;'>"
            "<tr style='background:#e2e8f0;'><th style='text-align:left; padding:8px;'>Reason</th><th style='text-align:left; padding:8px;'>Count</th></tr>"
            + ''.join(rows)
            + '</table>'
        )

    def _response_reason(self, response: Any) -> str:
        if not isinstance(response, dict):
            return '-'

        error = response.get('error')
        if error:
            return self._as_text(error)
        if response.get('success') and response.get('order_id'):
            return 'accepted'
        return '-'

    def _format_drivers(self, top_features: list[dict[str, Any]]) -> str:
        if not top_features:
            return '-'

        parts = []
        for item in top_features[:3]:
            parts.append(f"{self._as_text(item.get('feature', '-'))}: {float(item.get('contribution', 0.0)):.4f}")
        return ' | '.join(parts)

    def _as_text(self, value: Any) -> str:
        if value is None:
            return '-'
        if isinstance(value, date):
            return value.isoformat()
        return str(value)
