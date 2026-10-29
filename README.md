# MediPulse-Health-MongoDB
MediPulse is a healthcare management web application that connects patients and doctors, simplifies appointment booking, and manages healthcare data using MongoDB.

# MediPulse Health Web Dashboard

A Flask dashboard for the existing `MediPulseHealth` MongoDB Atlas database. It displays summary metrics, department revenue, prescribed medicines, patients and appointments, with create/edit/delete forms.

## Important safety notes
- This app does **not** drop, reset, or recreate any collection.
- It uses the existing `patients` and `appointments` collections and their current validators.
- Patient deletion is blocked while that patient still has appointments.
- Use synthetic/demo records only. This is an academic demo, not a production clinical system.
- Keep `.env` private and never commit it to GitHub. If a database password was exposed, rotate it in Atlas.


# MediPulse Health Management System
## Database-Focused Architecture and Data Flow

**Database:** `MediPulseHealth`  
**Collections:** `patients`, `appointments`  
**Database platform:** MongoDB Atlas  
**Application technologies:** Python, PyMongo, Flask, HTML, CSS, JavaScript

---

## 1. Purpose

MediPulse is a health-record management project that stores and retrieves patient and appointment information in MongoDB Atlas. Python code communicates with MongoDB through **PyMongo**. The command-line application demonstrates database setup, CRUD operations, schema validation, and aggregation queries. The Flask web application provides a browser interface for viewing and managing records.

This document focuses on the database architecture: where data is stored, how writes are validated, how queries return data, and how analytics are calculated.

## 2. High-Level Architecture (HLD)

The diagram below shows the system boundary and highlights MongoDB as the central data store.

```mermaid
flowchart TB
    USER([User])
    subgraph CLIENT["Presentation Layer"]
        BROWSER["Web browser<br/>HTML · CSS · JavaScript"]
    end
    subgraph APP["Python Application Layer"]
        FLASK["Flask routes<br/>Receive requests · Validate input"]
        LOGIC["Database / business logic"]
        CLI["Command-line application<br/>main.py"]
    end
    subgraph DRIVER["Database Access Layer"]
        PY["PyMongo client"]
        CONFIG["Environment configuration<br/>MONGO_URI in .env"]
    end
    subgraph ATLAS["MongoDB Atlas"]
        DB[("Database<br/>MediPulseHealth")]
        P[("patients<br/>collection")]
        A[("appointments<br/>collection")]
        DB --- P
        DB --- A
    end

    USER --> BROWSER
    BROWSER <-->|"HTTP request / response"| FLASK
    FLASK --> LOGIC
    CLI --> LOGIC
    LOGIC <-->|"CRUD queries / results"| PY
    CONFIG -.-> PY
    PY <-->|"MongoDB protocol over configured connection"| DB
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| Browser | Collects user input and displays records or analytics |
| Flask | Receives web requests, validates submitted data, and returns pages |
| Python database logic | Defines operations such as create, read, update, delete, and aggregation |
| PyMongo | Translates Python database calls into MongoDB operations and returns results |
| MongoDB Atlas | Hosts the database and executes reads, writes, validation, and aggregation |
| `MediPulseHealth` | Database containing the application's collections |
| `patients` | Stores patient documents |
| `appointments` | Stores appointment documents |

## 3. Database Structure

MongoDB is a document-oriented database. Data is stored as BSON documents inside collections, rather than rows inside relational tables.

```mermaid
flowchart TB
    CLUSTER["MongoDB Atlas cluster"]
    CLUSTER --> DB[("MediPulseHealth")]
    DB --> PC["patients collection"]
    DB --> AC["appointments collection"]
    PC --> P1["Patient document<br/>_id · patient fields"]
    PC --> P2["Patient document<br/>_id · patient fields"]
    AC --> A1["Appointment document<br/>_id · appointment fields"]
    AC --> A2["Appointment document<br/>_id · appointment fields"]
```

- **Cluster:** the Atlas-hosted MongoDB deployment.
- **Database:** `MediPulseHealth`, the logical container for the application's collections.
- **Collection:** a group of related documents, such as `patients`.
- **Document:** one record represented as a BSON object.
- **`_id`:** each document's unique identifier. MongoDB generates an `ObjectId` if the application does not provide an `_id`.

The exact document fields and validation requirements are defined in the project source code, especially `db_setup.py`. Check that file for the authoritative schema; this README intentionally does not invent field names.

## 4. How Data Is Stored

### Insert flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Browser / CLI
    participant App as Flask / Python logic
    participant Driver as PyMongo
    participant Atlas as MongoDB Atlas
    participant Col as Target collection

    User->>UI: Submit patient or appointment details
    UI->>App: Send request / function call
    App->>App: Validate and prepare document
    App->>Driver: insert_one(document)
    Driver->>Atlas: Send insert operation
    Atlas->>Col: Apply collection validator and insert
    alt Document is valid
        Col-->>Atlas: Document stored
        Atlas-->>Driver: Insert result and inserted_id
        Driver-->>App: Return result
        App-->>UI: Success response / updated page
    else Document is invalid
        Col-->>Atlas: Reject write
        Atlas-->>Driver: Validation error
        Driver-->>App: Raise database exception
        App-->>UI: Display a suitable error
    end
```

### Insert steps

1. The user submits a form or the Python program creates a document.
2. Application code validates input and prepares a Python dictionary.
3. PyMongo sends an `insert_one()` or `insert_many()` operation.
4. MongoDB checks the collection's configured validation rules.
5. If the document passes validation, MongoDB stores it and assigns `_id` if needed.
6. PyMongo returns the operation result to Python.
7. The application displays a confirmation or handles an error.

**Example only:** a MongoDB document is JSON-like. The fields below are illustrative, not a statement of the exact fields in your project.

```json
{
  "_id": "ObjectId generated by MongoDB",
  "exampleField": "example value"
}
```

## 5. How Data Is Fetched

### Read flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Browser
    participant Flask
    participant Driver as PyMongo
    participant Atlas as MongoDB Atlas
    participant Col as patients / appointments

    User->>UI: Open records page
    UI->>Flask: HTTP GET request
    Flask->>Driver: find(filter) or find_one(filter)
    Driver->>Atlas: Send read query
    Atlas->>Col: Find matching documents
    Col-->>Atlas: Matching documents
    Atlas-->>Driver: Cursor / result
    Driver-->>Flask: Python documents
    Flask->>Flask: Prepare template data
    Flask-->>UI: HTML response containing records
    UI-->>User: Display records
```

### Read steps

1. The user opens a records page or requests a particular record.
2. Flask calls the appropriate Python database function.
3. PyMongo sends a `find()` or `find_one()` query to Atlas.
4. MongoDB applies the filter and finds matching documents.
5. The results are returned to PyMongo. `find()` provides a cursor that the application can iterate over.
6. Flask passes the records to a template or formats them for a response.
7. The browser displays the records.

A query can return all documents or only documents that match a filter. The application should retrieve only the fields and records needed for the page.

## 6. Update and Delete Flow

```mermaid
flowchart TB
    USER["User chooses a record"]
    APP["Flask / Python application"]
    ID["Identify target document using its _id"]
    DECISION{"Operation"}
    UPDATE["PyMongo update_one(filter, update)"]
    DELETE["PyMongo delete_one(filter)"]
    DB[("MongoDB Atlas collection")]
    RESULT["Return operation result"]
    UI["Show updated list or status"]

    USER --> APP --> ID --> DECISION
    DECISION -->|"Update"| UPDATE
    DECISION -->|"Delete"| DELETE
    UPDATE --> DB
    DELETE --> DB
    DB --> RESULT --> UI
```

- **Update:** MongoDB locates a document using a filter and applies the requested changes, commonly with `$set`.
- **Delete:** MongoDB removes the document matching the filter.
- **Result:** PyMongo returns information such as matched, modified, or deleted counts. The application should handle the case where no document matches.

## 7. Database Schema Validation

MongoDB can validate document structure at the collection level. This project uses JSON Schema validators configured in its database setup code.

```mermaid
flowchart TD
    WRITE["Insert or update request"]
    VALIDATOR["MongoDB collection validator"]
    CHECK{"Document meets configured rules?"}
    STORE[("Store / update document")]
    REJECT["Reject write and return validation error"]

    WRITE --> VALIDATOR --> CHECK
    CHECK -->|"Yes"| STORE
    CHECK -->|"No"| REJECT
```

Validation rules can enforce requirements such as required fields and expected data types. The actual rules are defined by `db_setup.py`.

**Destructive-operation warning:** inspect `db_setup.py` before running database initialization. The current project setup may drop and recreate collections. Do not run initialization or a demonstration option that invokes it against important data unless a reset is intended and a backup exists.

## 8. How Dashboard Analytics Work

Aggregation lets MongoDB process data close to where it is stored. A pipeline passes documents through stages, where each stage filters, groups, sorts, joins, or reshapes data.

```mermaid
flowchart LR
    APP["Flask dashboard / Python analytics"]
    DRIVER["PyMongo aggregate()"]
    DB[("MongoDB Atlas")]
    MATCH["$match<br/>Filter documents"]
    GROUP["$group<br/>Calculate totals"]
    LOOKUP["$lookup<br/>Match related collection data"]
    SHAPE["$project / $sort<br/>Shape and order results"]
    RESULT["Return summary documents"]
    UI["Dashboard displays metrics"]

    APP --> DRIVER --> DB --> MATCH --> GROUP --> LOOKUP --> SHAPE --> RESULT --> UI
```

The stages shown are common examples. The exact pipeline order and stages depend on the actual code in `aggregations.py` and the Flask dashboard route. `$lookup` can combine matching information from another collection in the query result. It does not mean MongoDB permanently merges the two collections.

## 9. End-to-End Data Flow Summary

| User action | Application action | MongoDB action | Result |
|---|---|---|---|
| Add a patient | Validate form and call PyMongo | Insert into `patients` | New patient document |
| View patients | Execute a read query | Find matching documents | Patient list |
| Add an appointment | Validate form and call PyMongo | Insert into `appointments` | New appointment document |
| View appointments | Execute a read query | Find matching documents | Appointment list |
| Edit a record | Identify document and submit changes | Update matching document | Updated record |
| Delete a record | Identify selected document | Delete matching document | Record removed |
| Open analytics | Run aggregation pipeline | Filter, group, or join data | Summary metrics |

## 10. Connection Configuration

The application reads its Atlas connection URI from an environment variable, typically loaded from a local `.env` file.

```dotenv
MONGO_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.ama8rkz.mongodb.net/?retryWrites=true&w=majority
FLASK_SECRET_KEY=replace-with-a-long-random-secret
```

Replace placeholders locally. Never commit the real `.env` file or put a database password in this README. If a password has been exposed, rotate it in Atlas and update the local environment variable.

## 11. Security and Reliability Notes

- Create an Atlas database user with only the permissions the application needs.
- Restrict Atlas network access to approved IP addresses or networks.
- Keep `.env` in `.gitignore`.
- Use synthetic patient data for demos and development.
- Add authentication, authorization, secure deployment configuration, audit logging, and appropriate privacy controls before using real patient information.
- Back up important data and test schema changes against a development database.
- Use a production WSGI server and HTTPS for deployment; Flask's development server is for local development.
- Treat user-submitted values as untrusted and validate them before database operations.

## 12. Project Files Relevant to the Database

```text
MediPulse-Health-MongoDB/
├── app.py                 # Flask routes for the web dashboard
├── main.py                # Command-line menu / demonstrations
├── db_setup.py            # Database setup and schema validators
├── crud_ops.py            # Create, read, update, delete operations
├── aggregations.py        # Aggregation and $lookup examples
├── test_connection.py     # Atlas connectivity test
├── requirements.txt       # Python dependencies
├── .env                   # Local credentials; do not commit
├── templates/             # HTML pages
└── static/                # CSS and JavaScript
```

Filenames may vary in your local copy. Use the source files as the final authority for actual route names, schema fields, and query behavior.

---

**Project:** MediPulse Health Management System  
**Database:** `MediPulseHealth`  
**Collections:** `patients`, `appointments`
'''