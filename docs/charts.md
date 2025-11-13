# Charts and Visualizations

This document contains various charts and visualizations for the NFL Big Data Bowl 2026 project.

---

## Dataset Structure and Data Flow

This flowchart illustrates how the competition dataset captures NFL pass play execution across two distinct temporal phases: pre-pass tracking (INPUT) and post-pass tracking (OUTPUT). It shows the systematic player reduction from 12.3 to 3.3 tracked players based on proximity to the ball landing location.

```mermaid
flowchart TD
    A[Pre-Snap Setup] --> B[INPUT DATA<br/>Pre-Pass Tracking]
    B --> C{Ball Thrown?}
    C -->|Yes| D[OUTPUT DATA<br/>Post-Pass Tracking]
    D --> E[Catch / Incomplete]
    
    %% Input details
    B1["12.3 players tracked / 27.9 frames (2.8 sec)"] -.-> B
    B2["Roles: Passer, Targeted Receiver, Defense"] -.-> B
    
    %% Output details  
    D1["3.3 players tracked / 11.2 frames (1.2 sec)"] -.-> D
    D2["Selection: 1 Receiver + 2-3 Defenders"] -.-> D
    D3["Proximity: Tracked ≤12.4yd, Not >25.3yd"] -.-> D
    
    style B fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style D fill:#E24A4A,stroke:#8A2E2E,color:#fff
    style C fill:#F5A623,stroke:#8A6413,color:#000
```

**Key Insights:**
- The dataset isolates the contest for the ball by tracking only players positioned to impact the catch outcome
- Selection is proximity-based: tracked players average 12.4 yards from ball landing vs 25.3 yards for non-tracked players (p < 0.001)
- This structure enables precise measurement of execution quality during the critical 1.2-second window when passes are contested

---
