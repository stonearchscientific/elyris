from .db import init_db, get_session
from .models import Person, Document, Event, ErpBenefit, CrmProvider, CrmActivity, EhrEncounter, LmsIep, LmsGoal
from datetime import datetime, date, timedelta

if __name__ == "__main__":
    init_db()
    with get_session() as s:
        # Person (Spencer)
        sp = Person(first_name="Spencer", last_name="Kennedy", dob=date(2013,6,15),
                    legal_flags={"guardianship":"full","special_needs_trust":True})
        s.add(sp)
        s.commit()
        s.refresh(sp)

        # Document (waiver)
        doc = Document(person_id=sp.id, doc_type="medicaid_waiver",
                       extracted_fields={"renewal_date":"2026-01-15","case_worker":{"name":"Jane Doe","phone":"+1-612-555-9999"}})
        s.add(doc)

        # Event (IEP meeting)
        ev = Event(person_id=sp.id, title="IEP Annual Review", start_ts=datetime(2025,10,21,14,0), end_ts=datetime(2025,10,21,15,30),
                   event_metadata={"source":"lms-ieps","related_doc_id":doc.id})
        s.add(ev)

        # ERP benefit
        benefit = ErpBenefit(person_id=sp.id, benefit_name="Minnesota MA Waiver", status="active", renewal_date=date(2026,1,15),
                             case_worker={"name":"Jane Doe","phone":"+1-612-555-9999"})
        s.add(benefit)

        # CRM provider + activity
        prov = CrmProvider(name="Adaptive Swim Center", contact={"phone":"612-555-0001"})
        s.add(prov)
        s.commit()
        s.refresh(prov)
        act = CrmActivity(person_id=sp.id, provider_id=prov.id, activity_name="Adaptive Swim Lessons",
                          recurring_rule="RRULE:FREQ=WEEKLY;BYDAY=TU", notes="Instructor: Mike")
        s.add(act)

        # EHR encounter
        enc = EhrEncounter(person_id=sp.id, encounter_date=datetime(2025,9,12,10,30),
                           provider={"name":"Dr. Amy Patel","org":"Peds Clinic"},
                           summary="Annual well-child visit. Recommend continued OT.")
        s.add(enc)

        # LMS iep & goal
        iep = LmsIep(person_id=sp.id, iep_year=2025, next_review_date=date(2026,10,21))
        s.add(iep)
        s.commit()
        s.refresh(iep)
        goal = LmsGoal(iep_id=iep.id, goal_text="Improve expressive language to 3-word phrases across settings.", baseline="mostly 1-word outputs", target_date=date(2026,6,1))
        s.add(goal)

        s.commit()
    print("Seed complete. Database created at backend/data/elyris.db")
