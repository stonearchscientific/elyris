import React, { useEffect, useState } from "react";

type EventItem = { id: string, title: string, start_ts: string, metadata?: any };
type Benefit = { id: string, benefit_name: string, renewal_date: string, case_worker: any };

export default function UnifiedTimeline({ personId }: { personId?: string }) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [benefits, setBenefits] = useState<Benefit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // call backend endpoints
    const p = personId ? `?person_id=${personId}` : "";
    console.log("Fetching data with params:", p);
    
    Promise.all([
      fetch(`/api/v1/common/events${p}`).then(r => r.ok ? r.json() : []),
      fetch(`/api/v1/erp/benefits${p}`).then(r => r.ok ? r.json() : [])
    ]).then(([ev, bf]) => {
      console.log("Events:", ev);
      console.log("Benefits:", bf);
      setEvents(ev || []);
      setBenefits(bf || []);
      setLoading(false);
    }).catch(err => {
      console.error("Error fetching data:", err);
      setLoading(false);
    });
  }, [personId]);

  const benefitAsEvents = benefits.map(b => ({
    id: `benefit-${b.id}`,
    title: `${b.benefit_name} renewal`,
    start_ts: b.renewal_date,
    metadata: { type: "benefit", case_worker: b.case_worker }
  }));

  const timeline = [...events, ...benefitAsEvents].sort((a, b) => {
    const da = new Date(a.start_ts).getTime() || 0;
    const db = new Date(b.start_ts).getTime() || 0;
    return da - db;
  });

  if (loading) {
    return <div>Loading timeline...</div>;
  }

  return (
    <div>
      <h2>Unified timeline</h2>
      {timeline.length === 0 ? (
        <p>No events found.</p>
      ) : (
        <ul>
          {timeline.map(item => (
            <li key={item.id}>
              <strong>{item.title}</strong> — {new Date(item.start_ts || Date.now()).toLocaleString()}
              <pre style={{ whiteSpace: "pre-wrap" }}>{item.metadata ? JSON.stringify(item.metadata) : ""}</pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}