# Air Tracker: Flight Analytics
# SQL Analysis Queries
# Database: air_tracker

-- =====================================================
-- Query 1: Total flights per aircraft model
-- =====================================================

SELECT
    a.model AS aircraft_model,
    COUNT(f.flight_id) AS total_flights
FROM aircraft a
LEFT JOIN flight f
    ON a.registration = f.aircraft_registration
GROUP BY a.model
ORDER BY total_flights DESC;


-- =====================================================
-- Query 2: Aircraft assigned to more than 5 flights
-- =====================================================

SELECT
    a.registration,
    a.model,
    COUNT(f.flight_id) AS total_flights
FROM aircraft a
JOIN flight f
    ON a.registration = f.aircraft_registration
GROUP BY a.registration, a.model
HAVING COUNT(f.flight_id) > 5
ORDER BY total_flights DESC;


-- =====================================================
-- Query 3: Airports with more than 5 outbound flights
-- =====================================================

SELECT
    a.name AS airport_name,
    a.iata_code,
    COUNT(f.flight_id) AS outbound_flights
FROM airport a
JOIN flight f
    ON f.origin_iata = a.iata_code
GROUP BY a.airport_id, a.name, a.iata_code
HAVING COUNT(f.flight_id) > 5
ORDER BY outbound_flights DESC;


-- =====================================================
-- Query 4: Top 3 destination airports by arrivals
-- =====================================================

SELECT
    a.name AS airport_name,
    a.city,
    a.iata_code,
    COUNT(f.flight_id) AS arriving_flights
FROM airport a
JOIN flight f
    ON f.destination_iata = a.iata_code
GROUP BY a.airport_id, a.name, a.city, a.iata_code
ORDER BY arriving_flights DESC
LIMIT 3;


-- =====================================================
-- Query 5: Classify flights as Domestic or International
-- =====================================================

SELECT
    f.flight_number,
    f.origin_iata,
    f.destination_iata,
    CASE
        WHEN o.country IS NULL OR d.country IS NULL
             OR TRIM(o.country) = ''
             OR TRIM(d.country) = ''
            THEN 'Unknown'
        WHEN LOWER(TRIM(o.country)) = LOWER(TRIM(d.country))
            THEN 'Domestic'
        ELSE 'International'
    END AS flight_type
FROM flight f
LEFT JOIN airport o
    ON f.origin_iata = o.iata_code
LEFT JOIN airport d
    ON f.destination_iata = d.iata_code
ORDER BY f.flight_id;


-- =====================================================
-- Query 6: Five latest scheduled arrivals at DEL
-- Note: Actual arrival times are unavailable for DEL.
-- =====================================================

SELECT
    f.flight_number,
    f.aircraft_registration,
    ac.model AS aircraft_model,
    a.name AS departure_airport,
    f.scheduled_arrival
FROM flight f
LEFT JOIN aircraft ac
    ON f.aircraft_registration = ac.registration
LEFT JOIN airport a
    ON f.origin_iata = a.iata_code
WHERE f.destination_iata = 'DEL'
  AND f.scheduled_arrival IS NOT NULL
ORDER BY f.scheduled_arrival DESC
LIMIT 5;


-- =====================================================
-- Query 7: Airports with no recorded arriving flights
-- =====================================================

SELECT
    a.name AS airport_name,
    a.city,
    a.iata_code
FROM airport a
LEFT JOIN flight f
    ON f.destination_iata = a.iata_code
WHERE f.flight_id IS NULL
ORDER BY a.name;


-- =====================================================
-- Query 8: Flight status counts for each airline
-- =====================================================

SELECT
    COALESCE(f.airline_code, 'Unknown') AS airline,
    SUM(CASE WHEN f.status = 'Expected' THEN 1 ELSE 0 END)
        AS expected_flights,
    SUM(CASE WHEN f.status = 'Departed' THEN 1 ELSE 0 END)
        AS departed_flights,
    SUM(CASE WHEN f.status = 'Approaching' THEN 1 ELSE 0 END)
        AS approaching_flights,
    SUM(CASE WHEN f.status = 'Arrived' THEN 1 ELSE 0 END)
        AS arrived_flights,
    SUM(CASE WHEN f.status = 'Delayed' THEN 1 ELSE 0 END)
        AS delayed_flights,
    SUM(CASE WHEN f.status = 'Cancelled' THEN 1 ELSE 0 END)
        AS cancelled_flights,
    SUM(CASE WHEN f.status = 'Unknown' THEN 1 ELSE 0 END)
        AS unknown_flights
FROM flight f
GROUP BY f.airline_code
ORDER BY airline;


-- =====================================================
-- Query 9: Cancelled flights with aircraft and airports
-- =====================================================

SELECT
    f.flight_number,
    f.aircraft_registration,
    ac.model AS aircraft_model,
    o.name AS origin_airport,
    d.name AS destination_airport,
    f.scheduled_departure,
    f.status
FROM flight f
LEFT JOIN aircraft ac
    ON f.aircraft_registration = ac.registration
LEFT JOIN airport o
    ON f.origin_iata = o.iata_code
LEFT JOIN airport d
    ON f.destination_iata = d.iata_code
WHERE LOWER(TRIM(f.status)) = 'cancelled'
ORDER BY f.scheduled_departure DESC;


-- =====================================================
-- Query 10: City pairs with more than 2 aircraft models
-- =====================================================

SELECT
    o.city AS origin_city,
    d.city AS destination_city,
    COUNT(DISTINCT ac.model) AS different_aircraft_models
FROM flight f
JOIN airport o
    ON f.origin_iata = o.iata_code
JOIN airport d
    ON f.destination_iata = d.iata_code
JOIN aircraft ac
    ON f.aircraft_registration = ac.registration
GROUP BY o.city, d.city
HAVING COUNT(DISTINCT ac.model) > 2
ORDER BY different_aircraft_models DESC;


-- =====================================================
-- Query 11: Percentage of delayed arrivals per airport
-- Note: Based on flight.status; current data has no
-- rows with status = 'Delayed'.
-- =====================================================

SELECT
    a.name AS airport_name,
    a.city,
    a.iata_code,
    COUNT(f.flight_id) AS total_arrivals,
    SUM(
        CASE
            WHEN LOWER(TRIM(f.status)) = 'delayed' THEN 1
            ELSE 0
        END
    ) AS delayed_arrivals,
    ROUND(
        100.0 * SUM(
            CASE
                WHEN LOWER(TRIM(f.status)) = 'delayed' THEN 1
                ELSE 0
            END
        ) / NULLIF(COUNT(f.flight_id), 0),
        2
    ) AS delayed_percentage
FROM airport a
JOIN flight f
    ON f.destination_iata = a.iata_code
GROUP BY
    a.airport_id,
    a.name,
    a.city,
    a.iata_code
ORDER BY delayed_percentage DESC;
