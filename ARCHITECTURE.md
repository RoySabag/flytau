# FlyTau: System Architecture & Design Document

**Project:** FlyTau - Flight Management System  
**Date:** January 2026

---

## 1. Executive Summary
FlyTau is a full-stack Flight Management System designed to handle complex airline operations. It facilitates the entire lifecycle of flight scheduling, from aircraft management and crew assignment to ticket booking and financial reporting. The system is built with a focus on **data integrity**, **operational safety** (preventing double-bookings), and **scalable architecture**.

---

## 2. System Architecture

### 2.1 Architectural Pattern
The application follows a **Layered Architecture** leveraging the **MVC (Model-View-Controller)** pattern logic adapted for a Flask application with a Service Layer.

- **Presentation Layer (Routes/Templates)**:
    - **Blueprints**: Organized by domain (`admin_routes`, `auth`, `search`).
    - **Templates**: Jinja2 HTML templates using Bootstrap for responsive UI.
    - **Role**: Handles HTTP requests, input sanitization, and renders views.

- **Service Layer (`app/services`)**:
    - **Role**: Contains the *business logic* and orchestration. It bridges the gap between the Controller and the Data Access Layer.
    - **Key Services**:
        - `FlightService`: Orchestrates flight creation, including calling aircraft and crew sub-systems.
        - `SeatService`: Handles the complex logic of dynamic seat map generation.
        - `AuthService`: Manages user sessions and authentication.

- **Data Access Layer (`app/models/daos`)**:
    - **DAO Pattern**: Data Access Objects provide an abstract interface to the database.
    - **Role**: Executes raw SQL queries, handles transactions, and maps tuples to dictionaries.
    - **Key DAOs**: `FlightDAO`, `CrewScheduler`, `StatisticsDAO`.

- **Database Layer**:
    - **MySQL**: Relational database storing persistent state.

### 2.2 Directory Structure
```
flytau/
├── app/
│   ├── routes/          # Controllers (Admin, Auth, API)
│   ├── services/        # Business Logic (FlightService, SeatService)
│   ├── models/
│   │   └── daos/        # Data Access Objects (SQL interactions)
│   └── utils/           # Helper scripts (DB connection, verifiers)
├── templates/           # Frontend Views
└── run.py               # Application Entry Point
```

---

## 3. Database Schema Design

### 3.1 Core Entity Logic
A key design decision was the **removal of the static `seats` table** in favor of a **Configuration Model**.

- **Old Approach**: Storing 200+ rows for every flight's seats (Inefficient).
- **New Approach**: 
    - `aircraft_classes`: Defines the layout (e.g., "Boeing 737 has 20 rows of Economy").
    - `seats` (Dynamic): Generated on-the-fly for the UI.
    - `order_lines`: Stores the booked seat as `{"row": 12, "col": "A"}`.

### 3.2 Key Relationships
- **Flights**: The central entity linking `Routes`, `Aircraft`, and `Crew`.
- **Crew Assignments**: A Many-to-Many relationship between `Flights` and `Staff`.
- **Orders**: Linked to `Users` and containing multiple `OrderLines` (Tickets).

---

## 4. Key Algorithms & Logic

### 4.1 Intelligent Crew Scheduling (`CrewScheduler`)
The system employs a sophisticated algorithm to suggest and validate crew members.

- **Candidate Scoring**:
    - **Location**: Crew at the origin airport are prioritized (Score 0).
    - **Transfers**: Crew at other airports are flagged (Score 1) and a transfer flight is suggested.
    - **Certification**: Long-haul flights require certified staff.
- **Conflict Resolution (Overlap Check)**:
    - The system performs a temporal check to prevent double-booking.
    - **Logic**: A crew member is "Busy" if `(Existing_Start < New_End) AND (Existing_End > New_Start)`.
    - **Strict Validation**: Both the Wizard (UI) and the Backend reject concurrent assignments.

### 4.2 Dynamic Seat Map Generation (`SeatService`)
Instead of querying a massive table, the seat map is built dynamically:
1.  Fetch `aircraft_classes` to determine rows/cols for the aircraft type.
2.  Fetch `order_lines` for the specific flight to identify occupied seats.
3.  Merge the two datasets in memory to render the grid (Available/Occupied).

---

## 5. Security & Validation

To ensure "Score 100" reliability, the system implements multi-layer validation:

1.  **Date Integrity**:
    - **Past Flight Prevention**: Flights cannot be scheduled in the past.
    - **Implementation**: JS frontend restrictions (`min` attribute) + Strict Python backend checks.

2.  **Financial Safety**:
    - **Negative Price Guard**: Prevents operational errors where users are paid to fly.
    - **Implementation**: Guard clauses in `FlightService` reject negative values immediately.

3.  **Authentication**:
    - Role-based access control (Admin vs. User) protects sensitive headers and routes.

---

## 6. Logical Assumptions
1.  **Transfer Logic**: We assume a crew member can transfer if they arrive 2 hours before the next flight.
2.  **Aircraft Maintenance**: We currently assume aircraft are available if not in the air; maintenance windows are manual.
3.  **Pricing**: Prices are fixed per class per flight; dynamic pricing is a future extension.

---

## 7. Conclusion
FlyTau demonstrates a mature software engineering approach by decoupling concerns (Service Layer), optimizing data storage (Config-based Seats), and enforcing strict business rules (Crew Overlap, Date/Price Validation). This ensures a scalable, maintainable, and robust system.
