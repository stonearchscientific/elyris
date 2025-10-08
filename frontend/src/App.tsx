import React from "react";
import UnifiedTimeline from "./components/UnifiedTimeline";

export default function App(){
  // personId is the seeded Spencer; fetch /common/persons to get the id or hardcode seed value by reading backend DB.
  return (
    <div style={{padding:20}}>
      <h1>Elyris — Dashboard</h1>
      <UnifiedTimeline personId="" />
      <p>Open backend docs at <a href="http://localhost:8000/docs">/docs</a></p>
    </div>
  );
}
