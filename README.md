# FlyTau - Airline Management System

## System Architecture & Design

The application is built upon a **Layered Architecture**, ensuring separation of concerns, maintainability, and scalability.

### 1. Presentation Layer (`app/routes` + `app/templates`)
*   **Role**: Handles HTTP requests, input sanitization, and intelligent view rendering.
*   **Routes**: Organized by domain (e.g., `admin_routes`, `auth_routes`, `booking_routes`).
*   **Templates**: Server-side HTML rendering powered by **Jinja2**.

### 2. Service Layer (`app/services`)
*   **Role**: Encapsulates **Business Logic** and **Orchestration**. It acts as a bridge between the Controller (Routes) and the Data Access Layer.
*   **Facade Pattern**: This layer functions as a Facade, hiding the complexity of DAOs and raw logic from the presentation layer.
*   **Key Services**:
    *   `FlightService`: Orchestrates flight creation, invoking subsystems for aircraft and crew assignment.
    *   `SeatService`: Manages the complex logic of generating dynamic seat maps.
    *   `AuthService`: Handles user sessions, authentication, and security.

### 3. Data Access Layer (`app/models/daos`)
*   **Pattern**: **Data Access Object (DAO)**.
*   **Role**: Provides an abstract interface to the database. It executes raw SQL queries, manages transactions, and maps database tuples to Python dictionaries.
*   **Abstraction Benefit**: Decouples business logic from specific database implementation. Future migrations (e.g., to PostgreSQL or MongoDB) would only require changes in this layer.
*   **Examples**: `flight_dao`, `employee_dao`, `statistics_dao`.

### 4. Database Layer (`database`)
*   **DBManager**: Centralized class responsible for Connection Pooling, query execution, and resource cleanup.
*   **Singleton Pattern**: Implemented as a Singleton to ensure a unified access point for all application components, preventing connection leaks.
*   **MySQL**: Relational database managing the persistent state.

---

## Project Structure

```text
flytau/
├── app/
│   ├── routes/            # Intelligent Routing
│   ├── services/          # Business Logic & Orchestration
│   ├── models/
│   │   └── daos/          # Data Access Objects (SQL)
├── database/              # DB Connection & Pooling
├── templates/             # Frontend Views
└── run.py                 # Application Entry Point
```

---

## Core Algorithms

### 1. Intelligent Flight Scheduling
The system employs weighted algorithms to optimize resource allocation.

#### A. Aircraft Selection (`aircraft_service`)
The selection process operates in two stages:
1.  **Filtering (Hard Constraints)**:
    *   Eliminates aircraft already booked or flying.
    *   Prevents conflicts with future scheduled flights (chain logic).
    *   Enforces safety rules (e.g., "Small" aircraft cannot fly Long-Haul > 6 hours).

2.  **Scoring (Prioritization)**:
    Lower score indicates a better match.
    *   **0 Points**: Ideal Match (Correct location, Correct size).
    *   **+5 Points (Penalty)**: Inefficient Size (Using a "Big" plane for a short route).
    *   **+10 Points (Penalty)**: Ferry Flight Required (Aircraft is at a different airport and requires costly relocation).

#### B. Crew Selection (`crew_service`)
Crew members are selected based on a strict priority hierarchy:
1.  **Filtering**: Validates Role (Pilot/Attendant), Availability (Time Window), Location, and Certification (Long-Haul).
2.  **Prioritization** (Best to Worst):
    *   **Priority 1**: Local Crew + Exact Match (Most Efficient).
    *   **Priority 2**: Local Crew + Overqualified (e.g., Long-Haul Pilot on Short Route).
    *   **Priority 3**: Needs Transfer (Crew must be flown in).
    *   **Priority 4**: Needs Transfer + Overqualified (Least efficient).

#### C. Conflict Resolution
The system performs rigorous **Temporal Checks** to prevent double-booking.
*   **Logic**: A resource is "Busy" if `(Existing_Start < New_End) AND (Existing_End > New_Start)`.
*   **Validation**: Both the Frontend Wizard and Backend Services enforce these checks to reject overlapping assignments.

### 2. Dynamic Seat Mapping (`seat_service`)
Instead of storing millions of static seat records, the system generates seat maps on-the-fly:
1.  Fetches **Configuration** (`aircraft_classes`) to determine rows/columns for the specific aircraft.
2.  Fetches **Active Bookings** (`order_lines`) for the specific flight.
3.  **Merges** the data in-memory to render the real-time availability grid (Occupied/Free).

---

## Assumptions

*   **Admin Booking Restriction**: The ability for administrators to book flights directly has been removed from the UI per staff instructions (Admins must use the standard booking flow).
