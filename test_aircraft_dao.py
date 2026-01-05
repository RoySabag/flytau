from app.classes.db_manager import DB
from app.models.daos.aircrafts_dao import AircraftDAO

def test_aircraft_dao():
    dao = AircraftDAO(DB)
    
    # Test get_all_aircrafts
    print("--- All Aircrafts (id, type) ---")
    aircrafts = dao.get_all_aircrafts()
    if aircrafts:
        for a in aircrafts:
            print(a)
    else:
        print("No aircrafts found.")

    # Test get_crew_for_flight (Long Haul)
    print("\n--- Long Haul Crew (Pilots Cert=1 + Attendants) ---")
    crew_lh = dao.get_crew_for_flight(requires_long_haul=True)
    if crew_lh:
        print(f"Found {len(crew_lh)} qualified crew members.")
    else:
        print("No crew found.")

    # Test get_crew_for_flight (Short Haul / Any)
    print("\n--- All Crew ---")
    crew_all = dao.get_crew_for_flight(requires_long_haul=False)
    if crew_all:
         print(f"Found {len(crew_all)} total crew members.")

if __name__ == "__main__":
    test_aircraft_dao()
