# Interview Preparation

**1. Explain your project.**
I built a Cloud-Connected Smart Plant Care & Watering System. It collects
soil moisture, temperature, humidity, and light data and sends it to a
cloud backend. Since I didn't always have physical hardware, I built a
Python virtual IoT sensor that generates realistic readings — moisture
drifts down over time and rises when the plant is watered. The backend
validates and stores every reading in a cloud database, and an automation
engine compares moisture against a per-plant threshold to decide whether
to water. When it waters, it records the event, updates the dashboard, and
raises or resolves alerts. I also built device-offline detection, JWT and
API-key security, historical analytics, and a full automated test suite,
and deployed it to free-tier cloud hosting. The same backend accepts a
real ESP32 with no architecture changes.

**2. Why did you use cloud computing in this project?**
Cloud computing centralizes storage and processing so the dashboard is
reachable from anywhere, and it gives me managed databases, deployment
platforms, and monitoring for free at student scale — while the same
architecture (stateless API + managed database) scales to thousands of
devices without a redesign.

**3. How did you build the project without physical IoT hardware?**
I wrote a Python sensor simulator that behaves like a real device: it
posts JSON readings to the same REST endpoint an ESP32 would use, and it
models realistic trends — gradual drying, a rise in moisture while the
virtual pump runs, a day/night light curve — instead of pure random
numbers, so I could exercise the full watering-decision logic exactly as a
real deployment would.

**4. How does the automatic watering system work?**
Each plant has a moisture threshold and a target level (threshold +
margin). When a new reading arrives and the backend isn't already
watering, it starts the pump if moisture is below the threshold, the tank
isn't low, and the cooldown period has elapsed. It stops the pump once
moisture reaches the target, a maximum watering duration is hit (a safety
cutoff), or the tank runs low — whichever happens first — and logs the
whole event.

**5. How does data travel from the IoT device to the cloud?**
In the simulated version, the Python device sends JSON readings over HTTPS
to a REST API secured by an API key. The backend validates the payload,
stores it, and replies with the current pump command. In the advanced
real-hardware version, an ESP32 could use the same HTTPS approach or
publish to an MQTT broker for a larger device fleet.

**6. Why do IoT systems often use MQTT?**
MQTT is a lightweight publish-subscribe protocol built for constrained
devices and networks. Devices publish to topics through a broker instead
of talking to every consumer directly, which keeps bandwidth and battery
use low and scales cleanly to large device fleets — one of the reasons I
documented it as the upgrade path from this project's plain REST ingestion.

**7. How does your system detect an offline device?**
Every reading updates a `last_seen` timestamp on the device. A background
check compares the current time to `last_seen`; if the gap exceeds a
configured interval, the device is marked offline and a CRITICAL alert is
raised — the cloud equivalent of a heartbeat monitor, important because
missing data can mean a Wi-Fi, power, or sensor failure that a plant owner
needs to know about.

**8. How would your system handle 100,000 plants sending sensor readings?**
I'd put an API gateway in front of ingestion, run the backend as
autoscaling stateless instances behind it, add a queue to decouple
ingestion from the automation/alerting work, move to a time-series-capable
managed database with retention/rollup policies, and move the rate limiter
to a shared store like Redis so limits are enforced consistently across
instances.

**9. How did you test this project?**
I automated 25 scenarios: sensor generation and validation, API storage,
duplicate-reading rejection, moisture-threshold crossing in both
directions, automated and manual watering (including cooldown and
overwatering prevention), alert generation/acknowledgement/auto-resolution,
offline detection, historical queries, unauthorized access, and simulated
database/API failures — all run automatically with pytest.

**10. How can this project be improved further?**
Connect real ESP32 hardware over MQTT with a managed IoT broker, add
weather-forecast-aware watering and ML-based predictive watering, add a
physical tank float switch, add mobile push notifications, support
multiple plant zones per node, add solar power, and add anomaly detection
on the sensor stream.
