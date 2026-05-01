"""HTML report generation for daily ML stock picks."""

from datetime import date
from typing import Any


class MlReportService:
    """Build readable HTML report for long/short candidates and model explainability."""

    def build_html(
        self,
        report_date: date,
        horizon_days: int,
        threshold_pct: float,
        top_long: list[dict[str, Any]],
        top_short: list[dict[str, Any]],
        long_feature_importance: list[dict[str, Any]],
        short_feature_importance: list[dict[str, Any]],
        training_metrics: dict[str, dict[str, Any]],
    ) -> str:
        """Return a complete HTML report body."""
        long_rows = self._rows_html(top_long)
        short_rows = self._rows_html(top_short)

        long_importance_rows = self._importance_rows(long_feature_importance)
        short_importance_rows = self._importance_rows(short_feature_importance)

        long_metrics = training_metrics.get('long', {})
        short_metrics = training_metrics.get('short', {})

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>ML Signal Report - {report_date.isoformat()}</title>
</head>
<body style='font-family: Segoe UI, Arial, sans-serif; background:#f3f7fb; color:#1f2937; margin:0; padding:24px;'>
  <div style='max-width:1000px; margin:0 auto; background:#ffffff; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.06); overflow:hidden;'>
    <div style='background:#0f172a; color:#ffffff; padding:20px 24px;'>
      <h1 style='margin:0; font-size:24px;'>Atlas ML Signal Report</h1>
      <p style='margin:8px 0 0;'>Date: {report_date.isoformat()} | Horizon: {horizon_days} days | Move threshold: {threshold_pct:.2f}%</p>
    </div>

    <div style='padding:20px 24px;'>
      <h2 style='margin:0 0 12px; font-size:20px;'>Model Validation Snapshot</h2>
      <table style='width:100%; border-collapse:collapse; margin-bottom:20px;'>
        <tr style='background:#e2e8f0;'>
          <th style='text-align:left; padding:10px;'>Direction</th>
          <th style='text-align:left; padding:10px;'>Precision</th>
          <th style='text-align:left; padding:10px;'>Recall</th>
          <th style='text-align:left; padding:10px;'>Precision@5</th>
          <th style='text-align:left; padding:10px;'>Precision@10</th>
        </tr>
        <tr>
          <td style='padding:10px;'>Long</td>
          <td style='padding:10px;'>{float(long_metrics.get('precision', 0.0)):.4f}</td>
          <td style='padding:10px;'>{float(long_metrics.get('recall', 0.0)):.4f}</td>
          <td style='padding:10px;'>{float(long_metrics.get('precision_at_5', 0.0)):.4f}</td>
          <td style='padding:10px;'>{float(long_metrics.get('precision_at_10', 0.0)):.4f}</td>
        </tr>
        <tr>
          <td style='padding:10px;'>Short</td>
          <td style='padding:10px;'>{float(short_metrics.get('precision', 0.0)):.4f}</td>
          <td style='padding:10px;'>{float(short_metrics.get('recall', 0.0)):.4f}</td>
          <td style='padding:10px;'>{float(short_metrics.get('precision_at_5', 0.0)):.4f}</td>
          <td style='padding:10px;'>{float(short_metrics.get('precision_at_10', 0.0)):.4f}</td>
        </tr>
      </table>

      <h2 style='margin:0 0 12px; font-size:20px; color:#065f46;'>Top Long Candidates</h2>
      <table style='width:100%; border-collapse:collapse; margin-bottom:22px;'>
        <tr style='background:#dcfce7;'>
          <th style='text-align:left; padding:10px;'>Rank</th>
          <th style='text-align:left; padding:10px;'>Ticker</th>
          <th style='text-align:left; padding:10px;'>Confidence</th>
          <th style='text-align:left; padding:10px;'>Top Drivers</th>
        </tr>
        {long_rows}
      </table>

      <h2 style='margin:0 0 12px; font-size:20px; color:#7f1d1d;'>Top Short Candidates</h2>
      <table style='width:100%; border-collapse:collapse; margin-bottom:22px;'>
        <tr style='background:#fee2e2;'>
          <th style='text-align:left; padding:10px;'>Rank</th>
          <th style='text-align:left; padding:10px;'>Ticker</th>
          <th style='text-align:left; padding:10px;'>Confidence</th>
          <th style='text-align:left; padding:10px;'>Top Drivers</th>
        </tr>
        {short_rows}
      </table>

      <h2 style='margin:0 0 12px; font-size:20px;'>Global Feature Importance</h2>
      <div style='display:flex; gap:16px; flex-wrap:wrap;'>
        <div style='flex:1; min-width:320px;'>
          <h3 style='margin:0 0 8px; font-size:16px;'>Long Model</h3>
          <table style='width:100%; border-collapse:collapse;'>
            <tr style='background:#e2e8f0;'>
              <th style='text-align:left; padding:8px;'>Feature</th>
              <th style='text-align:left; padding:8px;'>Importance</th>
            </tr>
            {long_importance_rows}
          </table>
        </div>
        <div style='flex:1; min-width:320px;'>
          <h3 style='margin:0 0 8px; font-size:16px;'>Short Model</h3>
          <table style='width:100%; border-collapse:collapse;'>
            <tr style='background:#e2e8f0;'>
              <th style='text-align:left; padding:8px;'>Feature</th>
              <th style='text-align:left; padding:8px;'>Importance</th>
            </tr>
            {short_importance_rows}
          </table>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
        """.strip()

    def _rows_html(self, rows: list[dict[str, Any]]) -> str:
        """Render prediction rows for report table body."""
        if not rows:
            return "<tr><td colspan='4' style='padding:10px;'>No candidates generated</td></tr>"

        chunks: list[str] = []
        for row in rows:
            rank = row.get('rank') or '-'
            ticker = row.get('ticker', '-')
            confidence = float(row.get('confidence', 0.0))
            drivers = self._format_drivers(row.get('top_features', []))
            chunks.append(
                f"<tr><td style='padding:10px;'>{rank}</td><td style='padding:10px;'>{ticker}</td><td style='padding:10px;'>{confidence:.4f}</td><td style='padding:10px;'>{drivers}</td></tr>"
            )
        return ''.join(chunks)

    def _importance_rows(self, rows: list[dict[str, Any]]) -> str:
        """Render top global feature importance rows."""
        if not rows:
            return "<tr><td colspan='2' style='padding:8px;'>Not available</td></tr>"

        chunks: list[str] = []
        for row in rows[:10]:
            feature = row.get('feature', '-')
            importance = float(row.get('importance', 0.0))
            chunks.append(f"<tr><td style='padding:8px;'>{feature}</td><td style='padding:8px;'>{importance:.6f}</td></tr>")
        return ''.join(chunks)

    def _format_drivers(self, top_features: list[dict[str, Any]]) -> str:
        """Format per-stock top feature drivers for report readability."""
        if not top_features:
            return '-'

        parts = []
        for item in top_features:
            parts.append(f"{item.get('feature', '-')}: {float(item.get('contribution', 0.0)):.4f}")
        return ' | '.join(parts)
