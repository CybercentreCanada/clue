# Clue Demo Environment

This directory contains a docker-compose setup to run a local instance of Clue with Keycloak authentication.

## Authentication

Authentication is handled by a local Keycloak instance. The following users are available for testing:

| Username | Password | Roles/Groups |
|---|---|---|
| **goose** | `goose` | **Admin User** (DASI, airflow_admin, users-sg, hogwarts_user, clue_admin, clue_user) |
| **dewey** | `dewey` | airflow_user, hogwarts_user |
| **donald** | `donald` | DASI, airflow_admin, users-sg, hogwarts_user |
| **huey** | `huey` | airflow_user, users-sg, hogwarts_user, clue_user |
| **louie** | `louie` | DASI, airflow_user, hogwarts_user |
| **guest** | `guest` | airflow_user, hogwarts_user |

**Note:** Usernames and passwords match for all demo users.

## Accessing the Services

- **Clue UI:** [http://localhost](http://localhost)
- **Clue API:** [http://localhost:5000](http://localhost:5000)
- **Keycloak:** [http://localhost:9100](http://localhost:9100)
