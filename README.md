# Air Tracker: Flight Analytics



## Project Overview



Air Tracker: Flight Analytics is a Python, MySQL, and Streamlit project for collecting, storing, and analyzing flight and airport data. It provides a dashboard to explore flight records, airport information, aircraft, and airport delay statistics.



## Objectives



- Collect airport and flight information using API scripts.

- Store and query flight data in MySQL.

- Analyze flight counts, routes, aircraft usage, and airport statistics.

- Visualize flight and delay information through a Streamlit dashboard.

- Provide SQL queries for common flight analytics tasks.



## Technology Stack



- Python

- MySQL

- Streamlit

- Pandas

- Requests

- AeroDataBox API via RapidAPI (used by the API scripts)



## Project Structure



```text

Air\_Tracker\_Flight\_Analytics/

├── api/

│   ├── airport\_data.py

│   ├── flight\_api.py

│   ├── flight\_api\_backup.py

│   ├── airport\_delay\_api.py

│   ├── insert\_airport\_delay\_data.py

│   ├── airport\_delay\_analysis.py

│   ├── analyze\_saved\_delays.py

│   ├── airport\_delay\_chart.py

│   ├── airport\_cancellation\_chart.py

│   ├── airport\_data.json

│   ├── flight\_data.json

│   └── airport\_delay\_data.json

├── analysis/

├── dashboard/

│   └── app.py

├── database/

│   └── flight\_analysis\_queries.sql

├── .env

├── .gitignore

├── requirements.txt

└── test\_setup.py

```



Note: `aircraft\_api.py` currently has no implementation. Aircraft API collection should be considered incomplete until implemented and tested.



## Database



Database name: `air\_tracker`



Main tables:



- `airport` — airport codes, names, cities, countries, and location details.

- `aircraft` — aircraft registrations, models, manufacturers, and related details.

- `flight` — flight numbers, aircraft registrations, origin and destination airports, scheduled and actual times, statuses, and airline codes.

- `airport\_delays` — airport-level flight totals, delay statistics, cancellation counts, dates, and flight type.



A backup table named `flight\_backup\_before\_actual\_times` also exists in the current database. It is not part of the main dashboard workflow.



## Requirements



Install Python and MySQL, then install the required Python packages:



```powershell

python -m pip install -r requirements.txt

```



The project dependencies include:



- `requests`

- `pandas`

- `mysql-connector-python`

- `streamlit`



## Environment Configuration



Create or update the `.env` file in the project root with the configuration keys expected by the application.



Typical MySQL settings:



```text

MYSQL\_HOST=localhost

MYSQL\_USER=your\_mysql\_username

MYSQL\_PASSWORD=your\_mysql\_password

MYSQL\_DATABASE=air\_tracker

MYSQL\_PORT=3306

```



Configure the API credentials required by the API scripts using the variable names those scripts expect.



Do not commit `.env` or publish API keys and database passwords to GitHub. Use placeholder values in documentation, never real credentials.



## Running the Dashboard



Activate the project's virtual environment in PowerShell:



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



Start the Streamlit application:



```powershell

python -m streamlit run .\\dashboard\\app.py

```



Open the local URL shown in the terminal, usually:



`http://localhost:8501`



Keep the terminal running while using the dashboard.



## SQL Analytics



The file `database/flight\_analysis\_queries.sql` contains SQL analytics queries intended to cover:



1\. Flight counts by aircraft model.

2\. Aircraft assigned to more than five flight records.

3\. Airports with more than five outbound flight records.

4\. Top destination airports by arrival count.

5\. Domestic and international flight classification.

6\. Recent scheduled arrivals at Delhi Airport (DEL).

7\. Airports with no recorded arriving flights.

8\. Flight status counts by airline.

9\. Cancelled flights with aircraft and airport details.

10\. City pairs served by multiple aircraft models.

11\. Percentage of delayed arrivals by destination airport.



Run the queries against the `air\_tracker` database using a MySQL client. Review the SQL file before execution and ensure that the selected database is correct.



## Current Data Limitations



The current dataset has known limitations:



- Some flight records appear duplicated. Flight counts may therefore represent stored records rather than unique real-world flights.

- Current flight statuses include values such as `Expected`, `Departed`, `Approaching`, `Arrived`, and `Unknown`; the dataset currently contains no records with status `Delayed` or `Cancelled`.

- The `delayed\_flight` field in `airport\_delays` contains NULL values. These must not be interpreted as zero delayed flights.

- Actual arrival times are missing for some flights, including the currently recorded arrivals into DEL. The recent-arrivals query therefore uses scheduled arrival times where appropriate.

- Flight records and airport delay statistics cover different dates, so comparisons between them may not be time-aligned.

- Some flight destinations are absent from the airport reference table and consequently cannot always be classified as domestic or international.

- The aircraft API script is currently empty and requires implementation if direct aircraft API collection is needed.



These limitations should be addressed before drawing conclusions about actual delay rates, cancellations, or unique flight volumes.



## Future Improvements



- Implement and test aircraft API integration.

- Improve flight deduplication and data validation.

- Normalize scheduled and actual timestamps.

- Resolve missing delay counts using verified API field definitions.

- Align flight and delay statistics by airport and date.

- Add automated data-quality and database connection tests.

- Expand documentation for API collection and database population.

- Add screenshots and project results to the documentation.



## Security



Never upload real API keys, passwords, or other secrets to a public repository. Keep credentials in `.env` and verify `.gitignore` before pushing the project to GitHub.



## Project Status



The Streamlit dashboard is running, the main database tables contain data, and the SQL analytics file is available. Data-quality improvements, aircraft API implementation, and final documentation checks remain.



