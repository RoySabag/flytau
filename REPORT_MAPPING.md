# Admin Reports & Statistics Mapping

This document explains the connection between the queries in `StatisticsDAO` and the visualizations on the Admin Panel Reporting pages.

## 1. Occupancy Report
**Page URL**: `/dashboard/reports/occupancy`  
**Template**: `admin/reports/occupancy.html`

| Visual Element | Data Source Method (DAO) | Description |
| :--- | :--- | :--- |
| **KPI Metric** | `get_avg_fleet_occupancy()` | Displays the single large percentage number representing the average fleet efficiency. |
| **Recent Flights Table** | `get_recent_flights_occupancy(limit=5)` | Lists the last 5 landed flights with their individual occupancy rates. |

---

## 2. Revenue Report
**Page URL**: `/dashboard/reports/revenue`  
**Template**: `admin/reports/revenue.html`

| Visual Element | Data Source Method (DAO) | Description |
| :--- | :--- | :--- |
| **Revenue Charts** | `get_revenue_by_manufacturer()` | Provides data for Stacked Bar Charts showing Total Revenue grouped by Aircraft Manufacturer (Boeing/Airbus) and Cabin Class. |

---

## 3. Employee Hours Report
**Page URL**: `/dashboard/reports/hours`  
**Template**: `admin/reports/hours.html`

| Visual Element | Data Source Method (DAO) | Description |
| :--- | :--- | :--- |
| **Hours Distribution Table** | `get_employee_flight_hours()` | Lists employees (Pilots & Attendants) showing their flight hours split by "Short Haul" (< 6h) and "Long Haul" (> 6h). |

---

## 4. Cancellations Report
**Page URL**: `/dashboard/reports/cancellations`  
**Template**: `admin/reports/cancellations.html`

| Visual Element | Data Source Method (DAO) | Description |
| :--- | :--- | :--- |
| **Trend Chart** | `get_monthly_cancellation_rate()` | Provides a 6-month historical view of the cancellation rate percentage (calculated from confirmed vs. cancelled orders). |

---

## 5. Aircraft Activity Report
**Page URL**: `/dashboard/reports/activity`  
**Template**: `admin/reports/activity.html`

| Visual Element | Data Source Method (DAO) | Description |
| :--- | :--- | :--- |
| **Activity Dashboard** | `get_aircraft_activity_30_days()` | Shows a comprehensive view per aircraft for the last 30 days: total flights, utilization %, and most frequent route. |
